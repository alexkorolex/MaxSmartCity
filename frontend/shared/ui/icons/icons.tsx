import type { SVGProps } from 'react';

type IconProps = SVGProps<SVGSVGElement>;

function Icon({ width = 22, height = 22, ...rest }: IconProps) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden="true"
      {...rest}
    />
  );
}

export function ArrowLeftIcon(props: IconProps) {
  return <Icon {...props}><path d="m15 5-7 7 7 7" strokeLinecap="round" strokeLinejoin="round" /></Icon>;
}

export function PlusIcon(props: IconProps) {
  return <Icon {...props}><path d="M12 5v14M5 12h14" strokeLinecap="round" /></Icon>;
}

export function ActivityIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M3 12h4l2.2-5 4.2 10 2.2-5H21" strokeLinecap="round" strokeLinejoin="round" />
    </Icon>
  );
}

export function CityIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 20V8l5-3v15M9 10h7v10M16 13h4v7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M6.5 10.5h.01M6.5 14h.01M12 13h1M12 16h1M18 16h.01" strokeLinecap="round" />
    </Icon>
  );
}

export function HomeIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 11.5 12 4l8 7.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M6 10v9h12v-9" strokeLinecap="round" strokeLinejoin="round" />
    </Icon>
  );
}

export function ReportsIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <rect x="5" y="3.5" width="14" height="17" rx="2" />
      <path d="M8.5 8h7M8.5 12h7M8.5 16h4" strokeLinecap="round" />
    </Icon>
  );
}

export function NewsIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <rect x="3.5" y="5" width="17" height="14" rx="2" />
      <path d="M7 9h6M7 12.5h10M7 16h10" strokeLinecap="round" />
    </Icon>
  );
}

export function BellIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M6 10a6 6 0 1 1 12 0c0 3.5 1.2 5 1.2 5H4.8S6 13.5 6 10Z" strokeLinejoin="round" />
      <path d="M10 19a2 2 0 0 0 4 0" strokeLinecap="round" />
    </Icon>
  );
}

export function ProfileIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="8.5" r="3.5" />
      <path d="M5 20c1.2-4 4-6 7-6s5.8 2 7 6" strokeLinecap="round" />
    </Icon>
  );
}

export function HouseIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 11.5 12 4l8 7.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M6 10v9h4v-5h4v5h4v-9" strokeLinecap="round" strokeLinejoin="round" />
    </Icon>
  );
}

export function CheckCircleIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="m8.3 12.3 2.4 2.4 5-5.2" strokeLinecap="round" strokeLinejoin="round" />
    </Icon>
  );
}

export function WarningIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 4.5 21 19H3L12 4.5Z" strokeLinejoin="round" />
      <path d="M12 10v4" strokeLinecap="round" />
      <circle cx="12" cy="16.6" r="0.9" fill="currentColor" stroke="none" />
    </Icon>
  );
}

export function SettingsIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="3" />
      <path
        d="M19.4 13.5c.1-.5.1-1 0-1.5l1.8-1.4-1.5-2.6-2.2.6c-.4-.3-.8-.6-1.3-.8L15.8 5.6H12.2l-.4 2.2c-.5.2-.9.5-1.3.8l-2.2-.6-1.5 2.6L8.6 12c-.1.5-.1 1 0 1.5l-1.8 1.4 1.5 2.6 2.2-.6c.4.3.8.6 1.3.8l.4 2.2h3.6l.4-2.2c.5-.2.9-.5 1.3-.8l2.2.6 1.5-2.6-1.8-1.4Z"
        strokeLinejoin="round"
      />
    </Icon>
  );
}

export function HelpIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M9.6 9.5a2.4 2.4 0 1 1 3.4 2.2c-.8.4-1 .8-1 1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="16.7" r="0.9" fill="currentColor" stroke="none" />
    </Icon>
  );
}

export function InboxIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 12h4.5l1.5 2.5h4L15.5 12H20" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="4" y="6" width="16" height="13" rx="2" />
    </Icon>
  );
}
