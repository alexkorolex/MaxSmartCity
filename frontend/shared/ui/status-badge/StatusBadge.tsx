import { Typography } from '@maxhub/max-ui';

import './StatusBadge.css';

export type StatusTone = 'info' | 'success' | 'warning' | 'error' | 'neutral';

interface StatusBadgeProps {
  label: string;
  tone?: StatusTone;
}

export function StatusBadge({ label, tone = 'neutral' }: StatusBadgeProps) {
  return (
    <span className={`status-badge status-badge--${tone}`}>
      <Typography.Text variant="note-strong" color="inherit">
        {label}
      </Typography.Text>
    </span>
  );
}

export function ToneDot({ tone = 'neutral' }: { tone?: StatusTone }) {
  return <span className={`tone-dot tone-dot--${tone}`} aria-hidden="true" />;
}
