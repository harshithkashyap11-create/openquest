export default function MetricCard({ label, value, note, icon: Icon }) {
  return (
    <article className="metric-card">
      <div className="metric-topline">
        <span>{label}</span>
        {Icon && <Icon size={18} aria-hidden="true" />}
      </div>
      <strong className="metric-value">{value}</strong>
      {note && <span className="metric-note">{note}</span>}
    </article>
  );
}
