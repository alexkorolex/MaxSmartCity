import { Typography } from '@maxhub/max-ui';

export type StatusTone = 'info' | 'success' | 'warning' | 'error' | 'neutral';

const TONE_COLORS: Record<StatusTone, { background: string; text: string }> = {
  info: { background: 'color-mix(in srgb, var(--info) 16%, transparent)', text: 'var(--info)' },
  success: { background: 'color-mix(in srgb, var(--success) 16%, transparent)', text: 'var(--success)' },
  warning: { background: 'color-mix(in srgb, var(--warning) 20%, transparent)', text: 'var(--gray-dark)' },
  error: { background: 'color-mix(in srgb, var(--error) 14%, transparent)', text: 'var(--error)' },
  neutral: { background: 'var(--background-secondary)', text: 'var(--text-secondary)' },
};

interface StatusBadgeProps {
  label: string;
  tone?: StatusTone;
}

export function StatusBadge({ label, tone = 'neutral' }: StatusBadgeProps) {
  const colors = TONE_COLORS[tone];

  return (
    <span
      className="status-badge"
      style={{
        background: colors.background,
        color: colors.text,
      }}
    >
      <Typography.Text variant="note-strong" color="inherit">
        {label}
      </Typography.Text>
    </span>
  );
}

const TONE_SOLID_COLORS: Record<StatusTone, string> = {
  info: 'var(--info)',
  success: 'var(--success)',
  warning: 'var(--warning)',
  error: 'var(--error)',
  neutral: 'var(--gray)',
};

/** A small solid-color swatch for the same tone scale as `StatusBadge` - for compact
 * contexts (radio/checkbox rows) where a full pill badge would be too heavy. */
export function ToneDot({ tone = 'neutral' }: { tone?: StatusTone }) {
  return (
    <span
      style={{
        display: 'block',
        width: 10,
        height: 10,
        borderRadius: 'var(--radius-full)',
        background: TONE_SOLID_COLORS[tone],
      }}
    />
  );
}
