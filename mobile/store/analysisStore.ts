import { create } from 'zustand';
import type { AnalysisFreshness } from '@/lib/analysisHydrate';
import type { ActivityStep } from '@/lib/analysisLog';

export interface ThinkingStep {
  agent: string;
  step?: string;
  message: string;
  timestamp: number;
}

export interface AgentOutput {
  [key: string]: unknown;
}

export interface Prediction {
  direction: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  conviction: 'HIGH' | 'MEDIUM' | 'LOW';
  confidence_pct: number;
  target_price_range: [number | null, number | null];
  horizon_days: 7 | 14 | 30;
  rationale: string;
  key_signals: string[];
  risk_factors: string[];
  do_not_trade_if: string;
  valuation_note?: string;
  conflicts?: string[];
  agent_fundamental_verdict?: string;
  owner_fair_value_verdict?: string;
  analyzed_at?: string;
  analysis_source?: 'live' | 'cached';
}

type LoadStatus = 'idle' | 'loading' | 'ready' | 'error';

interface HydratePayload {
  prediction: Prediction;
  agentOutputs: Record<string, AgentOutput>;
  freshness: AnalysisFreshness;
}

interface AnalysisState {
  currentSymbol: string | null;
  isAnalysing: boolean;
  loadStatus: LoadStatus;
  analysisFreshness: AnalysisFreshness | null;
  streamingSteps: ThinkingStep[];
  activitySteps: ActivityStep[];
  agentOutputs: Record<string, AgentOutput>;
  prediction: Prediction | null;
  error: string | null;

  prepareSymbol: (symbol: string) => void;
  hydrateFromLatest: (payload: HydratePayload) => void;
  beginLiveAnalysis: (symbol: string) => void;
  setLoadStatus: (status: LoadStatus) => void;
  startAnalysis: (symbol: string) => void;
  addThinkingStep: (step: ThinkingStep) => void;
  addActivityStep: (step: ActivityStep) => void;
  setAgentOutput: (agent: string, data: AgentOutput) => void;
  setPrediction: (prediction: Prediction) => void;
  setError: (error: string) => void;
  resetAnalysis: () => void;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  currentSymbol: null,
  isAnalysing: false,
  loadStatus: 'idle',
  analysisFreshness: null,
  streamingSteps: [],
  activitySteps: [],
  agentOutputs: {},
  prediction: null,
  error: null,

  prepareSymbol: (symbol) =>
    set((s) => {
      if (s.currentSymbol === symbol && s.loadStatus === 'loading') return s;
      return {
        currentSymbol: symbol,
        isAnalysing: false,
        loadStatus: 'loading',
        analysisFreshness: null,
        streamingSteps: [],
        activitySteps: [],
        agentOutputs: {},
        prediction: null,
        error: null,
      };
    }),

  hydrateFromLatest: ({ prediction, agentOutputs, freshness }) =>
    set({
      prediction,
      agentOutputs,
      analysisFreshness: freshness,
      loadStatus: 'ready',
      isAnalysing: false,
      error: null,
    }),

  beginLiveAnalysis: (symbol) =>
    set({
      currentSymbol: symbol,
      isAnalysing: true,
      loadStatus: 'ready',
      streamingSteps: [],
      activitySteps: [],
      error: null,
    }),

  setLoadStatus: (loadStatus) => set({ loadStatus }),

  startAnalysis: (symbol) =>
    set({
      currentSymbol: symbol,
      isAnalysing: true,
      loadStatus: 'ready',
      streamingSteps: [],
      activitySteps: [],
      agentOutputs: {},
      prediction: null,
      analysisFreshness: null,
      error: null,
    }),

  addThinkingStep: (step) =>
    set((s) => ({ streamingSteps: [...s.streamingSteps, { ...step, timestamp: Date.now() }] })),

  addActivityStep: (step) =>
    set((s) => ({ activitySteps: [...s.activitySteps, step] })),

  setAgentOutput: (agent, data) =>
    set((s) => ({ agentOutputs: { ...s.agentOutputs, [agent]: data } })),

  setPrediction: (prediction) =>
    set((s) => ({
      prediction,
      isAnalysing: false,
      analysisFreshness: s.analysisFreshness
        ? { ...s.analysisFreshness, fresh: true, stale: false, ageMinutes: 0 }
        : {
            fresh: true,
            stale: false,
            ageMinutes: 0,
            ttlMinutes: 24 * 60,
            expiresInMinutes: 24 * 60,
            createdAt: prediction.analyzed_at ?? null,
          },
    })),

  setError: (error) => set({ error, isAnalysing: false, loadStatus: 'error' }),

  resetAnalysis: () =>
    set({
      currentSymbol: null,
      isAnalysing: false,
      loadStatus: 'idle',
      analysisFreshness: null,
      streamingSteps: [],
      activitySteps: [],
      agentOutputs: {},
      prediction: null,
      error: null,
    }),
}));
