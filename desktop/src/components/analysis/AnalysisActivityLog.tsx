import { useEffect, useRef } from 'react';
import type { ActivityStep, StepStatus } from '../../types/analysisLog';

const STATUS_ICON: Record<StepStatus, string> = {
  info: '○',
  running: '◐',
  done: '✓',
  error: '✕',
};

const STATUS_COLOR: Record<StepStatus, string> = {
  info: 'var(--text-muted)',
  running: 'var(--accent)',
  done: 'var(--green)',
  error: 'var(--red)',
};

const AGENT_COLOR: Record<string, string> = {
  fundamental: '#a78bfa',
  technical: '#34d399',
  sentiment: '#fbbf24',
  ml: '#60a5fa',
  orchestrator: '#f472b6',
  system: 'var(--text-muted)',
};

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

type Props = {
  steps: ActivityStep[];
  isActive?: boolean;
  maxHeight?: number;
};

export function AnalysisActivityLog({ steps, isActive, maxHeight = 280 }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [steps.length]);

  if (steps.length === 0) {
    return (
      <div className="card analysis-log" style={{ marginBottom: 24, padding: '14px 18px' }}>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
          {isActive ? 'Waiting for analysis steps…' : 'Run analysis to see a step-by-step activity log here.'}
        </p>
      </div>
    );
  }

  let lastPhase = '';

  return (
    <div className="card analysis-log" style={{ marginBottom: 24, padding: '14px 18px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.8 }}>
            Activity log
          </div>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '4px 0 0', fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>
            Live steps as the pipeline runs — expand “How analysis works” above for the full picture.
          </p>
        </div>
        {isActive && (
          <span className="badge badge-accent" style={{ fontSize: 10 }}>
            Live
          </span>
        )}
      </div>

      <div
        className="analysis-log-scroll"
        style={{ maxHeight, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}
      >
        {steps.map((step, index) => {
          const status = step.status ?? 'info';
          const showPhaseHeader = step.phaseLabel && step.phaseLabel !== lastPhase;
          if (showPhaseHeader) lastPhase = step.phaseLabel ?? '';

          return (
            <div key={step.id}>
              {showPhaseHeader && (
                <div
                  style={{
                    fontSize: 10,
                    fontWeight: 800,
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: 0.6,
                    marginTop: index > 0 ? 10 : 0,
                    marginBottom: 6,
                  }}
                >
                  {step.phaseLabel}
                </div>
              )}
              <div className="analysis-log-row" data-status={status}>
                <span style={{ color: STATUS_COLOR[status], fontWeight: 700, width: 14, flexShrink: 0 }}>
                  {STATUS_ICON[status]}
                </span>
                <span style={{ color: 'var(--text-muted)', fontSize: 10, fontVariantNumeric: 'tabular-nums', width: 62, flexShrink: 0 }}>
                  {formatTime(step.timestamp)}
                </span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    color: AGENT_COLOR[step.agent ?? 'system'] ?? 'var(--accent)',
                    width: 88,
                    flexShrink: 0,
                    textTransform: 'capitalize',
                  }}
                >
                  {step.agentLabel ?? step.agent ?? '—'}
                </span>
                <span style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.45, flex: 1 }}>
                  {step.message}
                </span>
              </div>
              {step.detail && (
                <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '2px 0 4px 88px', lineHeight: 1.4 }}>
                  {step.detail}
                </p>
              )}
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
