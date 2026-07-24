// Admin sidebar/UI uchun chiziqli ikonkalar.
interface IconProps {
  size?: number;
  color?: string;
  strokeWidth?: number;
}

const base = (color: string, strokeWidth: number) => ({
  fill: 'none',
  stroke: color,
  strokeWidth,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
});

export function DashboardIcon({ size = 20, color = 'currentColor', strokeWidth = 1.8 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base(color, strokeWidth)}>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </svg>
  );
}

export function OrdersIcon({ size = 20, color = 'currentColor', strokeWidth = 1.8 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base(color, strokeWidth)}>
      <rect x="4" y="3" width="16" height="18" rx="2" />
      <path d="M8 8h8M8 12h8M8 16h5" />
    </svg>
  );
}

export function DriversIcon({ size = 20, color = 'currentColor', strokeWidth = 1.8 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base(color, strokeWidth)}>
      <rect x="1" y="7" width="13" height="9" rx="1.5" />
      <path d="M14 10h4l3 3v3h-3" />
      <circle cx="6" cy="18" r="1.8" />
      <circle cx="17" cy="18" r="1.8" />
    </svg>
  );
}

export function UsersIcon({ size = 20, color = 'currentColor', strokeWidth = 1.8 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base(color, strokeWidth)}>
      <circle cx="9" cy="8" r="3.2" />
      <path d="M3 20c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5" />
      <path d="M16 5.2a3.2 3.2 0 010 5.9M17.5 20c0-2.6-1-4.4-2.6-5.4" />
    </svg>
  );
}

export function TruckTypesIcon({ size = 20, color = 'currentColor', strokeWidth = 1.8 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base(color, strokeWidth)}>
      <path d="M3 6l9-3 9 3-9 3-9-3z" />
      <path d="M3 6v7l9 3 9-3V6M12 9v7" />
    </svg>
  );
}

export function SearchIconAdmin({ size = 16, color = 'var(--color-gray-500)', strokeWidth = 2 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base(color, strokeWidth)}>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" />
    </svg>
  );
}

export function PlusIconAdmin({ size = 16, color = '#fff', strokeWidth = 2.2 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base(color, strokeWidth)}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function EditIcon({ size = 16, color = 'var(--color-gray-700)', strokeWidth = 1.8 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base(color, strokeWidth)}>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4z" />
    </svg>
  );
}

export function TrashIcon({ size = 16, color = 'var(--color-danger)', strokeWidth = 1.8 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base(color, strokeWidth)}>
      <path d="M4 7h16M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2M6 7l1 13a1 1 0 001 1h8a1 1 0 001-1l1-13" />
    </svg>
  );
}

export function LogoutIcon({ size = 18, color = 'var(--color-gray-500)', strokeWidth = 1.8 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base(color, strokeWidth)}>
      <path d="M15 4h3a1 1 0 011 1v14a1 1 0 01-1 1h-3" />
      <path d="M10 8l-4 4 4 4M6 12h11" />
    </svg>
  );
}

export function CloseIconAdmin({ size = 20, color = 'var(--color-gray-600)', strokeWidth = 2 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base(color, strokeWidth)}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}
