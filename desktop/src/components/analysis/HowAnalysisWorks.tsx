import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ANALYSIS_PIPELINE_INTRO, ANALYSIS_PIPELINE_STEPS } from '../../content/howAnalysisWorks';

export function HowAnalysisWorks({ defaultOpen = false }: { defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="card card-flat" style={{ marginBottom: 16 }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{
          width: '100%',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: 0,
          textAlign: 'left',
        }}
        aria-expanded={open}
      >
        <div>
          <p className="section-label" style={{ marginBottom: 4 }}>How analysis works</p>
          <p style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.5, margin: 0 }}>
            {open ? 'Step-by-step pipeline for this stock' : 'Tap to see how StockSage runs multi-agent analysis'}
          </p>
        </div>
        <span style={{ fontSize: 18, color: 'var(--accent)', flexShrink: 0, marginLeft: 12 }}>
          {open ? '▾' : '▸'}
        </span>
      </button>

      {open && (
        <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: 16 }}>
            {ANALYSIS_PIPELINE_INTRO}
          </p>
          <ol style={{ margin: 0, paddingLeft: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 14 }}>
            {ANALYSIS_PIPELINE_STEPS.map((s) => (
              <li key={s.step} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <span
                  style={{
                    flexShrink: 0,
                    width: 26,
                    height: 26,
                    borderRadius: '50%',
                    background: 'var(--accent-dim)',
                    color: 'var(--accent)',
                    fontSize: 12,
                    fontWeight: 800,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {s.step}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', marginBottom: 4 }}>{s.title}</div>
                  <p style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.55, margin: 0 }}>{s.summary}</p>
                  {s.detail && (
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5, marginTop: 6, marginBottom: 0 }}>
                      {s.detail}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ol>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 16, marginBottom: 0 }}>
            <Link to="/guide#how-analysis-works" style={{ color: 'var(--accent)', fontWeight: 600 }}>
              Full guide →
            </Link>
            {' · '}
            Watch the <strong style={{ color: 'var(--text-2)', fontWeight: 600 }}>Activity log</strong> below for live progress.
          </p>
        </div>
      )}
    </div>
  );
}
