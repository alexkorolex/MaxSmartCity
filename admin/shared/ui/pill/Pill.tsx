export type PillTone = 'info' | 'success' | 'warning' | 'error' | 'neutral';

interface PillProps {
  label: string;
  tone?: PillTone;
}

export function Pill({ label, tone = 'neutral' }: PillProps) {
  return <span className={`pill pill--${tone}`}>{label}</span>;
}
