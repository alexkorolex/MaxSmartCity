import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="state-block">
      {icon && <div className="state-block__icon">{icon}</div>}
      <strong>{title}</strong>
      {description && <span>{description}</span>}
      {action}
    </div>
  );
}
