import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { createChart, IChartApi, CandlestickData } from 'lightweight-charts';
import { useQuery } from '@tanstack/react-query';
import { apiClient, WS_URL } from '../api';
import { ValueInvestingPanel } from '../components/investor/ValueInvestingPanel';
import { GuideLink } from '../components/ui/GuideLink';
import { SymbolLabel } from '../components/ui/SymbolLabel';
import { AnalysisActivityLog } from '../components/analysis/AnalysisActivityLog';
import { HowAnalysisWorks } from '../components/analysis/HowAnalysisWorks';
import {
  formatAnalysisAge,
  hydrateFromLatestPayload,
  type AnalysisFreshness,
} from '../lib/analysisHydrate';
import { normalizeWsLogMessage, type ActivityStep } from '../types/analysisLog';

const DIR_COLOR: Record<string, string> = {
  BULLISH: 'var(--green)', BEARISH: 'var(--red)', NEUTRAL: 'var(--yellow)',
};

export function StockDetail() {
  const { symbol } = useParams<{ symbol: string }>();
  const chartRef = useRef<HTMLDivElement>(null);
  const chartApi = useRef<IChartApi | null>(null);

  const [activitySteps, setActivitySteps] = useState<ActivityStep[]>([]);
  const [agentOutputs, setAgentOutputs] = useState<Record<string, any>>({});
  const [prediction, setPrediction] = useState<any>(null);
  const [freshness, setFreshness] = useState<AnalysisFreshness | null>(null);
  const [loadStatus, setLoadStatus] = useState<'loading' | 'ready'>('loading');
  const [wsStatus, setWsStatus] = useState<'idle' | 'connecting' | 'streaming' | 'done' | 'error'>('idle');
  const wsRef = useRef<WebSocket | null>(null);

  const { data: history } = useQuery({
    queryKey: ['history', symbol],
    queryFn: () => apiClient.get(`/stocks/${symbol}/history`, { params: { period: '3mo' } }).then((r) => r.data),
    enabled: !!symbol,
  });

  const { data: quote } = useQuery({
    queryKey: ['quote', symbol],
    queryFn: () => apiClient.get(`/stocks/${symbol}/quote`).then((r) => r.data),
    enabled: !!symbol,
    refetchInterval: 60_000,
  });

  // Chart
  useEffect(() => {
    if (!chartRef.current || !history?.length) return;
    if (chartApi.current) chartApi.current.remove();

    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: 280,
      layout: { background: { color: 'var(--surface)' } as any, textColor: '#8BA3CC' },
      grid: { vertLines: { color: '#1E2D4A' }, horzLines: { color: '#1E2D4A' } },
    });
    chartApi.current = chart;

    const series = chart.addCandlestickSeries({
      upColor: '#10B981', downColor: '#F43F5E',
      borderUpColor: '#10B981', borderDownColor: '#F43F5E',
      wickUpColor: '#10B981', wickDownColor: '#F43F5E',
    });

    const candles: CandlestickData[] = history
      .filter((d: any) => d.date && d.open)
      .map((d: any) => ({ time: d.date as string, open: d.open, high: d.high, low: d.low, close: d.close }));

    series.setData(candles);
    chart.timeScale().fitContent();
    return () => { chart.remove(); chartApi.current = null; };
  }, [history]);

  // Cache-first: load saved analysis on symbol change; agents only when user clicks Refresh
  useEffect(() => {
    if (!symbol) return;
    let cancelled = false;
    setLoadStatus('loading');
    setActivitySteps([]);
    setAgentOutputs({});
    setPrediction(null);
    setFreshness(null);
    setWsStatus('idle');

    (async () => {
      try {
        const { data } = await apiClient.get(`/stocks/${symbol}/analysis/latest`);
        if (cancelled) return;
        const hydrated = hydrateFromLatestPayload(data);
        if (hydrated) {
          setPrediction(hydrated.prediction);
          setAgentOutputs(hydrated.agentOutputs);
          setFreshness(hydrated.freshness);
        }
      } catch {
        /* no saved analysis */
      } finally {
        if (!cancelled) setLoadStatus('ready');
      }
    })();

    return () => {
      cancelled = true;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [symbol]);

  const runAnalysis = useCallback(() => {
    if (!symbol) return;
    let gotLivePrediction = false;
    setActivitySteps([]);
    setAgentOutputs({});
    setPrediction(null);
    setWsStatus('connecting');

    const token = localStorage.getItem('ss_token');
    wsRef.current?.close();
    const ws = new WebSocket(`${WS_URL}/ws/analyze/${symbol}?token=${token ?? ''}&force=1`);
    wsRef.current = ws;

    const loadCachedFallback = async () => {
      if (gotLivePrediction) return;
      try {
        const { data } = await apiClient.get(`/stocks/${symbol}/analysis/latest`);
        const hydrated = hydrateFromLatestPayload(data);
        if (hydrated) {
          setPrediction(hydrated.prediction);
          setAgentOutputs(hydrated.agentOutputs);
          setFreshness(hydrated.freshness);
        }
        setWsStatus('done');
      } catch {
        setWsStatus('error');
      }
    };

    ws.onopen = () => setWsStatus('streaming');
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      const step = normalizeWsLogMessage(msg);
      if (step) setActivitySteps((p) => [...p, step]);
      if (msg.type === 'agent_complete') setAgentOutputs((p) => ({ ...p, [msg.agent]: msg.output_json }));
      else if (msg.type === 'prediction_complete') {
        gotLivePrediction = true;
        const { type: _t, ...pred } = msg;
        setPrediction({
          ...pred,
          analysis_source: msg.analysis_source === 'cached' ? 'cached' : 'live',
        });
        setFreshness((f) =>
          f
            ? { ...f, fresh: true, stale: false, ageMinutes: 0 }
            : {
                fresh: true,
                stale: false,
                ageMinutes: 0,
                ttlMinutes: 24 * 60,
                expiresInMinutes: 24 * 60,
                createdAt: pred.analyzed_at ?? null,
              },
        );
        setWsStatus('done');
        ws.close();
      } else if (msg.type === 'error') {
        setWsStatus('error');
        loadCachedFallback();
      }
    };
    ws.onerror = () => {
      if (!gotLivePrediction) loadCachedFallback();
    };
    ws.onclose = () => {
      wsRef.current = null;
      if (!gotLivePrediction) loadCachedFallback();
    };
  }, [symbol]);

  const pos = (quote?.change_pct ?? 0) >= 0;
  const isRunning = wsStatus === 'connecting' || wsStatus === 'streaming';
  const hasAnalysis = Boolean(prediction);
  const needsRefresh = loadStatus === 'ready' && (!hasAnalysis || (freshness?.stale ?? false));

  const statusLabel = isRunning
    ? 'Analysing…'
    : loadStatus === 'loading'
      ? 'Loading…'
      : freshness?.fresh && hasAnalysis
        ? `Saved ${formatAnalysisAge(freshness.ageMinutes)}`
        : needsRefresh
          ? hasAnalysis
            ? 'Stale — refresh'
            : 'No analysis'
          : 'Ready';
  const statusClass = isRunning
    ? 'badge-accent'
    : freshness?.fresh && hasAnalysis
      ? 'badge-green'
      : needsRefresh
        ? 'badge-red'
        : 'badge-accent';

  return (
    <div className="page">
      <header className="page-header-row" style={{ marginBottom: 24 }}>
        <div>
          {quote?.company_name || quote?.base_ticker ? (
            <SymbolLabel item={quote} showName />
          ) : (
            <h1 style={{ fontSize: 28, fontWeight: 900, color: 'var(--text)', letterSpacing: -1 }}>{symbol}</h1>
          )}
          {quote?.price != null && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 6 }}>
              <span style={{ fontSize: 26, fontWeight: 800, color: 'var(--text)' }}>
                ₹{quote.price.toLocaleString('en-IN')}
              </span>
              <span className={pos ? 'badge-green' : 'badge-red'} style={{ fontSize: 14 }}>
                {pos ? '+' : ''}{quote.change_pct?.toFixed(2)}%
              </span>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className={`badge ${statusClass}`}>{isRunning ? '⚡ ' : ''}{statusLabel}</span>
          {(needsRefresh || (freshness?.fresh && hasAnalysis)) && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={runAnalysis}
              disabled={isRunning}
            >
              {hasAnalysis ? 'Refresh analysis' : 'Run analysis'}
            </button>
          )}
        </div>
      </header>

      <div style={{ marginBottom: 16, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <GuideLink section="stock-quote" label="Price & chart" />
        <GuideLink section="ai-agents" label="AI agents" />
        <GuideLink section="ai-prediction" label="Prediction labels" />
        <GuideLink section="owner-investing" label="Owner investing" />
        <GuideLink section="how-analysis-works" label="How analysis works" />
      </div>

      {/* Chart */}
      <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 24 }}>
        <div ref={chartRef} style={{ background: 'var(--surface)' }} />
      </div>

      {symbol && <ValueInvestingPanel symbol={symbol} />}

      <HowAnalysisWorks />

      <AnalysisActivityLog
        steps={activitySteps}
        isActive={isRunning}
      />

      {/* Agent outputs */}
      {Object.entries(agentOutputs).length > 0 && (
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
          {Object.entries(agentOutputs).map(([agent, output]: [string, any]) => (
            <div key={agent} className="card" style={{ padding: '10px 14px', flex: '1 1 180px' }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 6 }}>
                {agent} ✓
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-2)' }}>
                {output?.signal ?? output?.valuation_verdict ?? output?.sentiment_signal ?? '—'}
              </div>
            </div>
          ))}
        </div>
      )}


      {/* Prediction */}
      {prediction && (
        <div className="card prediction-card" style={{ borderLeftColor: DIR_COLOR[prediction.direction] ?? 'var(--border)' }}>
          <p className="section-label">AI prediction</p>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
            <span className="prediction-direction" style={{ color: DIR_COLOR[prediction.direction] ?? 'var(--text)' }}>
              {prediction.direction}
            </span>
            <div style={{ display: 'flex', gap: 6 }}>
              <span className={prediction.direction === 'BULLISH' ? 'badge-green' : prediction.direction === 'BEARISH' ? 'badge-red' : ''} style={{ fontSize: 13, padding: '4px 12px' }}>
                {prediction.conviction}
              </span>
              <span style={{ background: 'var(--card-hover)', color: 'var(--text-2)', borderRadius: 6, padding: '4px 12px', fontSize: 13 }}>
                {prediction.confidence_pct}% conf
              </span>
            </div>
          </div>

          {prediction.target_price_range?.[0] != null && (
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)', marginBottom: 10 }}>
              Target ₹{prediction.target_price_range[0]?.toLocaleString('en-IN')} – ₹{prediction.target_price_range[1]?.toLocaleString('en-IN')}
            </div>
          )}

          <p style={{ fontSize: 14, color: 'var(--text-2)', lineHeight: 1.7, marginBottom: 14 }}>{prediction.rationale}</p>

          {prediction.key_signals?.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 }}>
                Key Signals
              </div>
              {prediction.key_signals.map((s: string, i: number) => (
                <div key={i} style={{ fontSize: 13, color: 'var(--text-2)', marginBottom: 4 }}>• {s}</div>
              ))}
            </div>
          )}

          {prediction.do_not_trade_if && (
            <div style={{
              fontSize: 13, color: 'var(--yellow)',
              background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)',
              borderRadius: 8, padding: '10px 14px',
            }}>
              ⛔ {prediction.do_not_trade_if}
            </div>
          )}
        </div>
      )}

      <p style={{ marginTop: 24, fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 }}>
        StockSage AI provides AI-generated research and tools for informational use. It is not investment advice
        or a recommendation from a SEBI-registered adviser. Past performance does not guarantee future results.
        You are responsible for your own decisions.{' '}
        <GuideLink section="legal" label="Read more" />
      </p>
    </div>
  );
}
