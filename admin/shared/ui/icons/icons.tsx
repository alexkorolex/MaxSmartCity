import type { SVGProps } from 'react';

type IconProps = SVGProps<SVGSVGElement>;

function Icon({ width = 18, height = 18, ...rest }: IconProps) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      {...rest}
    />
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

export function HousesIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M3 20.5h18" strokeLinecap="round" />
      <path d="M4.5 20.5v-9L9.5 7l5 4.5v9" strokeLinejoin="round" />
      <path d="M14.5 11.5 17 9.5l3 2.5v8.5" strokeLinejoin="round" />
      <path d="M8 20.5v-4h3v4" />
    </Icon>
  );
}

export function BuildingIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <rect x="5" y="3.5" width="14" height="17" rx="1.5" />
      <path d="M8.5 7.5h.01M12 7.5h.01M15.5 7.5h.01M8.5 11h.01M12 11h.01M15.5 11h.01M8.5 14.5h.01M15.5 14.5h.01" strokeLinecap="round" />
      <path d="M10 20.5v-4h4v4" />
    </Icon>
  );
}

export function StaffIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="9" cy="8" r="3" />
      <path d="M3.5 19c1-3.3 3-5 5.5-5s4.5 1.7 5.5 5" strokeLinecap="round" />
      <circle cx="17" cy="8.5" r="2.2" />
      <path d="M15.3 12.2c2 .2 3.3 1.7 4.2 4.6" strokeLinecap="round" />
    </Icon>
  );
}

export function PersonIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="8.5" r="3.5" />
      <path d="M5 20c1.2-4 4-6 7-6s5.8 2 7 6" strokeLinecap="round" />
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

export function CommentIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 5.5h16v10H9l-4 3.5v-3.5H4Z" strokeLinejoin="round" />
      <path d="M8 9.5h8M8 12.5h5" strokeLinecap="round" />
    </Icon>
  );
}

export function SendIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m4 4 17 8-17 8 3-8-3-8Z" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M7 12h14" strokeLinecap="round" />
    </Icon>
  );
}

export function LogOutIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M9 4H5.5A1.5 1.5 0 0 0 4 5.5v13A1.5 1.5 0 0 0 5.5 20H9" strokeLinecap="round" />
      <path d="M14 16l4-4-4-4M18 12H9" strokeLinecap="round" strokeLinejoin="round" />
    </Icon>
  );
}

export function SearchIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m20 20-4.3-4.3" strokeLinecap="round" />
    </Icon>
  );
}

export function ChevronRightIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m9 5 7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
    </Icon>
  );
}

export function ArrowLeftIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M19 12H5M11 6l-6 6 6 6" strokeLinecap="round" strokeLinejoin="round" />
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

export function InboxIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 12h4.5l1.5 2.5h4L15.5 12H20" strokeLinecap="round" strokeLinejoin="round" />
      <rect x="4" y="6" width="16" height="13" rx="2" />
    </Icon>
  );
}

export function CityIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 20V9l5-3v14M9 20V6l6-3v17M15 20V11l5 2v7" strokeLinejoin="round" />
    </Icon>
  );
}

export function SunIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="4" />
      <path
        d="M12 3v2M12 19v2M5 5l1.4 1.4M17.6 17.6 19 19M3 12h2M19 12h2M5 19l1.4-1.4M17.6 6.4 19 5"
        strokeLinecap="round"
      />
    </Icon>
  );
}

export function MoonIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" strokeLinejoin="round" />
    </Icon>
  );
}

export function MenuIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round" />
    </Icon>
  );
}

export function CloseIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m6 6 12 12M18 6 6 18" strokeLinecap="round" />
    </Icon>
  );
}
