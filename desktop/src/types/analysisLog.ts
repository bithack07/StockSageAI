/** User-facing activity log entry from WebSocket step_log events. */
export type StepStatus = 'info' | 'running' | 'done' | 'error';

export interface ActivityStep {
  id: string;
  type: string;
  phase?: string;
  phaseLabel?: string;
  agent?: string;
  agentLabel?: string;
  status?: StepStatus;
  message: string;
  detail?: string;
  timestamp: number;
}

export function normalizeWsLogMessage(msg: Record<string, unknown>): ActivityStep | null {
  const ts = typeof msg.timestamp === 'number' ? msg.timestamp : Date.now() / 1000;

  if (msg.type === 'step_log') {
    return {
      id: `${ts}-${msg.phase}-${msg.agent}-${msg.message}`,
      type: 'step_log',
      phase: msg.phase as string | undefined,
      phaseLabel: (msg.phase_label as string) ?? undefined,
      agent: msg.agent as string | undefined,
      agentLabel: (msg.agent_label as string) ?? undefined,
      status: (msg.status as StepStatus) ?? 'info',
      message: String(msg.message ?? ''),
      detail: msg.detail as string | undefined,
      timestamp: ts,
    };
  }

  if (msg.type === 'data_refresh' || msg.type === 'analysis_start') {
    return {
      id: `${ts}-${msg.type}`,
      type: String(msg.type),
      phase: 'data',
      phaseLabel: 'Market data',
      agent: 'system',
      agentLabel: 'System',
      status: msg.type === 'analysis_start' ? 'running' : 'info',
      message: String(msg.message ?? (msg.type === 'analysis_start' ? 'Starting multi-agent analysis…' : 'Loading data…')),
      timestamp: ts,
    };
  }

  if (msg.type === 'agent_thinking') {
    return {
      id: `${ts}-think-${msg.agent}`,
      type: 'agent_thinking',
      phase: 'agents',
      phaseLabel: 'Specialist agents',
      agent: msg.agent as string | undefined,
      agentLabel: String(msg.agent ?? 'agent'),
      status: 'running',
      message: String(msg.message ?? msg.step ?? ''),
      timestamp: ts,
    };
  }

  // agent_complete updates result tiles only — step_log already has friendly done lines
  if (msg.type === 'agent_complete') {
    return null;
  }

  if (msg.type === 'prediction_start' || msg.type === 'prediction_complete') {
    return null;
  }

  if (msg.type === 'analysis_saved') {
    return null;
  }

  if (msg.type === 'error') {
    return {
      id: `${ts}-error`,
      type: 'error',
      phase: 'data',
      phaseLabel: 'Error',
      agent: 'system',
      agentLabel: 'System',
      status: 'error',
      message: String(msg.message ?? 'Something went wrong'),
      timestamp: ts,
    };
  }

  return null;
}
