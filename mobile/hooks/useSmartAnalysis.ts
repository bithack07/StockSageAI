import { useCallback, useEffect, useRef } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { WS_BASE, stocks } from '@/api/client';
import { hydrateFromLatestPayload } from '@/lib/analysisHydrate';
import { normalizeWsLogMessage } from '@/lib/analysisLog';
import { useAnalysisStore, type Prediction } from '@/store/analysisStore';

function parsePredictionPayload(msg: Record<string, unknown>): Prediction {
  const { type: _t, ...rest } = msg;
  return rest as Prediction;
}

export function useSmartAnalysis(symbol: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const gotLivePrediction = useRef(false);
  const {
    prepareSymbol,
    hydrateFromLatest,
    beginLiveAnalysis,
    addActivityStep,
    setAgentOutput,
    setPrediction,
    setError,
    setLoadStatus,
    analysisFreshness,
    loadStatus,
    isAnalysing,
    prediction,
  } = useAnalysisStore();

  const closeWs = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  const connectWs = useCallback(
    async (force: boolean) => {
      if (!symbol) return;

      const token = await AsyncStorage.getItem('access_token');
      if (!token) {
        setError('Sign in to run live analysis.');
        return;
      }

      closeWs();
      gotLivePrediction.current = false;
      beginLiveAnalysis(symbol);

      const forceQ = force ? '&force=1' : '';
      const ws = new WebSocket(
        `${WS_BASE}/ws/analyze/${symbol}?token=${encodeURIComponent(token)}${forceQ}`,
      );
      wsRef.current = ws;

      const loadCachedFallback = async () => {
        if (gotLivePrediction.current) return;
        try {
          const { data } = await stocks.latestAnalysis(symbol);
          const hydrated = hydrateFromLatestPayload(data);
          if (hydrated) hydrateFromLatest(hydrated);
          else setLoadStatus('ready');
        } catch {
          setError('Analysis unavailable. Check backend is running and API URL is correct.');
        }
      };

      ws.onmessage = (event) => {
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
                analysis_source: msg.analysis_source === 'cached' ? 'cached' : 'live',
              });
              closeWs();
              break;
            case 'error':
              setError(msg.message);
              closeWs();
              loadCachedFallback();
              break;
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onerror = () => {
        if (!gotLivePrediction.current) loadCachedFallback();
      };

      ws.onclose = (ev) => {
        wsRef.current = null;
        if (ev.code === 4401) {
          setError('Session expired. Please sign in again.');
          return;
        }
        if (!gotLivePrediction.current) loadCachedFallback();
      };
    },
    [
      symbol,
      closeWs,
      beginLiveAnalysis,
      addActivityStep,
      setAgentOutput,
      setPrediction,
      setError,
      hydrateFromLatest,
      setLoadStatus,
    ],
  );

  const runAnalysis = useCallback(() => {
    connectWs(true);
  }, [connectWs]);

  useEffect(() => {
    if (!symbol) return;

    let cancelled = false;
    prepareSymbol(symbol);

    (async () => {
      try {
        const { data } = await stocks.latestAnalysis(symbol);
        if (cancelled) return;
        const hydrated = hydrateFromLatestPayload(data);
        if (hydrated) {
          hydrateFromLatest(hydrated);
          return;
        }
        setLoadStatus('ready');
      } catch {
        if (!cancelled) {
          setError('Could not load saved analysis. Tap Refresh to try again.');
        }
      }
    })();

    return () => {
      cancelled = true;
      closeWs();
    };
  }, [symbol, prepareSymbol, hydrateFromLatest, setLoadStatus, setError, closeWs]);

  const hasAnalysis = Boolean(prediction);
  const needsRefresh =
    loadStatus === 'ready' && (!hasAnalysis || (analysisFreshness?.stale ?? false));

  return {
    runAnalysis,
    needsRefresh,
    isFresh: analysisFreshness?.fresh ?? false,
    freshness: analysisFreshness,
    loadStatus,
    isAnalysing,
    hasAnalysis,
  };
}
