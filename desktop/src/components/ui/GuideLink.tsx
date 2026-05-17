import { Link } from 'react-router-dom';

type Props = {
  section?: string;
  label?: string;
  className?: string;
};

/** Link to the in-app metrics guide (optional section anchor). */
export function GuideLink({ section, label = 'What do these mean?', className }: Props) {
  const to = section ? `/guide#${section}` : '/guide';
  return (
    <Link
      to={to}
      className={className ?? 'guide-link'}
      style={{
        fontSize: 12,
        fontWeight: 600,
        color: 'var(--accent)',
        textDecoration: 'none',
      }}
    >
      ℹ {label}
    </Link>
  );
}
