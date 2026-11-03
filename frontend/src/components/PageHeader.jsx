export default function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  context,
}) {
  return (
    <header className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1 tabIndex={-1}>{title}</h1>
        {context && <p className="page-context">{context}</p>}
        {description && <p className="page-description">{description}</p>}
      </div>
      {actions && <div className="page-heading-actions">{actions}</div>}
    </header>
  );
}
