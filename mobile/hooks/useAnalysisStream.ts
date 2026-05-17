import { useEffect, useRef } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { WS_BASE, stocks } from '@/api/client';
import { normalizeWsLogMessage } from '@/lib/analysisLog';
import { useAnalysisStore, type Prediction } from '@/store/analysisStore';

function parsePredictionPayload(msg: Record<string, unknown>): Prediction {
  const { type: _t, ...rest } = msg;
  return rest as Prediction;
}

export function useAnalysisStream(symbol: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const gotLivePrediction = useRef(false);
  const {
    startAnalysis,
    addActivityStep,
    setAgentOutput,
    setPrediction,
    setError,
  } = useAnalysisStore();

  useEffect(() => {
    if (!symbol) return;

    let cancelled = false;
    gotLivePrediction.current = false;

    const connect = async () => {
      const token = await AsyncStorage.getItem('access_token');
      if (!token) {
        setError('Sign in to run live analysis.');
        return;
      }

      startAnalysis(symbol);
      const ws = new WebSocket(`${WS_BASE}/ws/analyze/${symbol}?token=${encodeURIComponent(token)}`);
      wsRef.current = ws;

      const loadCached = async () => {
        if (gotLivePrediction.current) return;
        try {
          const { data } = await stocks.latestAnalysis(symbol);
          if (cancelled || !data?.prediction) return;
          const pred =
            typeof data.prediction === 'string' ? JSON.parse(data.prediction) : data.prediction;
          setPrediction({
            ...pred,
            analyzed_at: data.created_at ?? pred.analyzed_at,
            analysis_source: 'cached',
          });
        } catch {
          if (!cancelled) setError('Analysis unavailable. Check backend is running and API URL is correct.');
        }
      };

      ws.onmessage = (event) => {
        if (cancelled) return;
        try {
          const msg = JSON.parse(event.data);
          const step = normalizeWsLogMessage(msg);
          if (step) addActivityStep(step);

          switch (msg.type) {
            case 'agent_complete':
              setAgentOutput(msg.agent, msg.output_json);
              break;
            case 'prediction_complete':
              gotLivePrediction.current = true;
              setPrediction({
                ...parsePredictionPayload(msg),
                analysis_source: 'live',
              });
              ws.close();
              break;
            case 'error':
              setError(msg.message);
              ws.close();
              loadCached();
              break;
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onerror = () => {
        if (!cancelled && !gotLivePrediction.current) loadCached();
      };

      ws.onclose = (ev) => {
        wsRef.current = null;
        if (!cancelled && ev.code === 4401) {
          setError('Session expired. Please sign in again.');
          return;
        }
        if (!cancelled && !gotLivePrediction.current) loadCached();
      };
    };

    connect();

    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [symbol]);

  return { ws: wsRef.current };
}
