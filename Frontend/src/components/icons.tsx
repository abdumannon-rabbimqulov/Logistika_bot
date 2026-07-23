// Dizayn fayllaridan olingan inline SVG ikonkalar (chiziq/stroke uslubi, emoji yo'q).
// Har biri size/color/strokeWidth props qabul qiladi — turli holatlarda (tanlangan/tanlanmagan)
// qayta ishlatish uchun.

interface IconProps {
  size?: number;
  color?: string;
  strokeWidth?: number;
}

export function BackIcon({ size = 18, color = 'var(--color-gray-800)', strokeWidth = 2 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

/** "Mening joylashuvim" (locate me) tugmasi — nishon/crosshair uslubidagi ikonka. */
export function LocationIcon({ size = 20, color = 'var(--color-gray-800)', strokeWidth = 1.9 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
    </svg>
  );
}

/** Manzillarni almashtirish (swap) tugmasi ikonkasi. */
export function SwapIcon({ size = 18, color = 'var(--color-gray-800)', strokeWidth = 1.9 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 3l-4 4 4 4M4 7h13M16 21l4-4-4-4M20 17H7" />
    </svg>
  );
}

export function CalendarIcon({ size = 19, color = 'var(--color-gray-800)', strokeWidth = 1.9 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="16" rx="3" />
      <path d="M8 2v4M16 2v4M3 10h18" />
    </svg>
  );
}

/** Destination (manzilga) qatoridagi bayroqcha ikonka. */
export function DestinationFlagIcon({ size = 20, color = 'var(--color-gray-900)', strokeWidth = 1.8 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 3v18" />
      <path d="M5 4h11l-2 4 2 4H5" />
    </svg>
  );
}

export function SearchIcon({ size = 13, color = 'var(--color-gray-500)', strokeWidth = 2 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" />
    </svg>
  );
}

export function PlusIcon({ size = 13, color = 'var(--color-gray-500)', strokeWidth = 2.2 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function ClockIcon({ size = 14, color = 'var(--color-gray-500)', strokeWidth = 2 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 3" />
    </svg>
  );
}

export function CardIcon({ size = 19, color = 'var(--color-gray-700)', strokeWidth = 1.7 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="6" width="20" height="12" rx="2" />
      <circle cx="12" cy="12" r="2.5" />
    </svg>
  );
}

export function SettingsIcon({ size = 18, color = 'var(--color-gray-700)', strokeWidth = 1.7 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 6h6M14 6h6M4 12h11M19 12h1M4 18h3M11 18h9" />
      <circle cx="12" cy="6" r="2" />
      <circle cx="15" cy="12" r="2" />
      <circle cx="8" cy="18" r="2" />
    </svg>
  );
}

export function BellIcon({ size = 18, color = '#0F1319', strokeWidth = 1.8 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8a6 6 0 10-12 0c0 4-2 5-2 6h16c0-1-2-2-2-6" />
      <path d="M10 20a2 2 0 004 0" />
    </svg>
  );
}

export function ProfileIcon({ size = 17, color = '#0F1319', strokeWidth = 1.8 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4 3.5-7 8-7s8 3 8 7" />
    </svg>
  );
}

export function PinIcon({ size = 20, color = 'var(--color-accent)', strokeWidth = 1.9 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 21s-7-6.2-7-11a7 7 0 0114 0c0 4.8-7 11-7 11z" />
      <circle cx="12" cy="10" r="2.4" />
    </svg>
  );
}

export function ChevronRightIcon({ size = 18, color = 'var(--color-gray-500)', strokeWidth = 2 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}

export function InfoIcon({ size = 20, color = '#0F1319', strokeWidth = 1.7 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v5M12 16h.01" />
    </svg>
  );
}

export function HomeAddressIcon({ size = 16, color = '#0F1319', strokeWidth = 1.8 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 11l9-8 9 8" />
      <path d="M5 10v10h14V10" />
    </svg>
  );
}

export function WorkAddressIcon({ size = 16, color = '#0F1319', strokeWidth = 1.8 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="7" width="18" height="13" rx="2" />
      <path d="M8 7V5a2 2 0 012-2h4a2 2 0 012 2v2" />
    </svg>
  );
}

export function HomeNavIcon({ size = 21, color = 'var(--color-accent)', strokeWidth = 1.9 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 11l9-8 9 8" />
      <path d="M5 10v10h14V10" />
    </svg>
  );
}

export function OrdersNavIcon({ size = 21, color = 'var(--color-gray-500)', strokeWidth = 1.7 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="7" width="18" height="14" rx="2" />
      <path d="M3 11h18M9 15h6" />
    </svg>
  );
}

export function MessagesNavIcon({ size = 21, color = 'var(--color-gray-500)', strokeWidth = 1.7 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
    </svg>
  );
}

// ── Transport turi ikonkalari ─────────────────────────────────────────────

export function VanIcon({ size = 24, color = 'var(--color-gray-500)', strokeWidth = 1.6 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="9" width="13" height="8" rx="1.5" />
      <path d="M15 11h4l3 3v3h-3" />
      <circle cx="6.5" cy="18.5" r="1.6" />
      <circle cx="16.5" cy="18.5" r="1.6" />
    </svg>
  );
}

export function TentTruckIcon({ size = 24, color = 'var(--color-accent)', strokeWidth = 1.6 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="8" width="15" height="9" rx="1.5" />
      <path d="M16 11h4l3 3v3h-3" />
      <circle cx="6.5" cy="19" r="1.7" />
      <circle cx="17.5" cy="19" r="1.7" />
    </svg>
  );
}

export function ReeferIcon({ size = 24, color = 'var(--color-gray-500)', strokeWidth = 1.6 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2v20M4.5 6.5l15 11M19.5 6.5l-15 11M4 12h16M6 4l2.5 2.5M17.5 4L15 6.5M6 20l2.5-2.5M17.5 20L15 17.5" />
    </svg>
  );
}

export function FlatbedIcon({ size = 24, color = 'var(--color-gray-500)', strokeWidth = 1.6 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-5 9 5-9 5-9-5z" />
      <path d="M3 9v7l9 5 9-5V9M12 14v7" />
    </svg>
  );
}

export function IsothermIcon({ size = 24, color = 'var(--color-gray-500)', strokeWidth = 1.6 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="2" width="16" height="20" rx="3" />
      <path d="M9 8h6M12 6v6" />
    </svg>
  );
}

/** Nom bo'yicha eng mos ikonni tanlaydi (backend truck-type nomlari erkin matn). */
export function truckIconFor(name: string) {
  const n = name.toLowerCase();
  if (n.includes('sovut') || n.includes('reefer') || n.includes('muzlat')) return ReeferIcon;
  if (n.includes('tent')) return TentTruckIcon;
  if (n.includes('bort') || n.includes('flatbed')) return FlatbedIcon;
  if (n.includes('izoterm') || n.includes('isotherm')) return IsothermIcon;
  return VanIcon;
}
