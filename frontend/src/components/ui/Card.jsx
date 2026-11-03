export default function Card({
  as: Element = 'article',
  variant = 'default',
  className = '',
  children,
  ...props
}) {
  return (
    <Element className={`cp-card cp-card-${variant} ${className}`} {...props}>
      {children}
    </Element>
  );
}
