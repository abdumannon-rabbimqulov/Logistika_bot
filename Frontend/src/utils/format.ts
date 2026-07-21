export function formatPrice(value: number): string {
  return Math.round(value).toLocaleString('uz-UZ').replace(/,/g, ' ');
}

export function formatEta(minutesFromNow: number): string {
  const eta = new Date(Date.now() + minutesFromNow * 60_000);
  return eta.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit', hour12: false });
}

export function formatRelativeDate(iso: string): string {
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const diffDays = Math.floor(diffMs / (24 * 60 * 60 * 1000));
  if (diffDays <= 0) return 'Bugun';
  if (diffDays === 1) return 'Kecha';
  if (diffDays < 7) return `${diffDays} kun oldin`;
  const weeks = Math.floor(diffDays / 7);
  if (weeks === 1) return "1 hafta oldin";
  if (weeks < 5) return `${weeks} hafta oldin`;
  return date.toLocaleDateString('uz-UZ');
}

export function routeLabel(originAddress: string | null | undefined, destinationAddress: string | null | undefined): string {
  return `${originAddress ?? '?'} → ${destinationAddress ?? '?'}`;
}

const STATUS_LABELS: Record<string, string> = {
  SCHEDULED: 'Rejalashtirilgan',
  PENDING: 'Qidirilmoqda',
  ACCEPTED: "Qabul qilindi",
  IN_PROGRESS: "Yo'lda",
  COMPLETED: 'Yakunlandi',
  CANCELLED: 'Bekor qilindi',
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}
