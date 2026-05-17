import { useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { METRICS_GUIDE_SECTIONS } from '../content/metricsGuide';
import { PageHeader } from '../components/ui/PageHeader';

export function Guide() {
  const { hash } = useLocation();
  const activeId = hash.replace('#', '') || null;

  const sections = useMemo(() => METRICS_GUIDE_SECTIONS, []);

  useEffect(() => {
    if (activeId) {
      document.getElementById(activeId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [activeId]);

  return (
    <div className="page page-wide">
      <PageHeader
        title="Metrics guide"
        subtitle="What every number, index, and label on StockSage AI means — focused on Indian markets (NSE/BSE)"
      />

      <div className="card card-flat" style={{ marginBottom: 24, padding: 16 }}>
        <p style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.6, marginBottom: 12 }}>
          Jump to a section:
        </p>
        <div className="chip-row">
          {sections.map((s) => (
            <a key={s.id} href={`#${s.id}`} className="chip" style={{ textDecoration: 'none' }}>
              {s.title.split('(')[0].trim()}
            </a>
          ))}
        </div>
      </div>

      {sections.map((section) => (
        <section key={section.id} id={section.id} className="card" style={{ marginBottom: 16 }}>
          <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: section.intro ? 8 : 14, color: 'var(--text)' }}>
            {section.title}
          </h2>
          {section.intro && (
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.55 }}>{section.intro}</p>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {section.items.map((item) => (
              <div key={item.term} style={{ borderLeft: '2px solid var(--border-light)', paddingLeft: 14 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--accent)', marginBottom: 4 }}>{item.term}</div>
                <p style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.55, margin: 0 }}>{item.explanation}</p>
                {item.example && (
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6, fontStyle: 'italic' }}>Example: {item.example}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      ))}

      <p style={{ textAlign: 'center', marginTop: 8 }}>
        <Link to="/" className="btn btn-ghost btn-sm">← Back to dashboard</Link>
      </p>
    </div>
  );
}
