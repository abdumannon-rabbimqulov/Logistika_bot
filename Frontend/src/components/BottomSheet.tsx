import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import styles from './BottomSheet.module.css';

/** Panelning to'xtash nuqtalari (ekran balandligining ulushi sifatida).
 *  `peek` — xarita deyarli to'liq ochiq; `full` — panel butun ekranni egallaydi. */
export type SheetSnap = 'peek' | 'half' | 'full';

const SNAP_RATIO: Record<SheetSnap, number> = {
  peek: 0.28,
  half: 0.55,
  full: 0.92,
};

const ORDER: SheetSnap[] = ['peek', 'half', 'full'];

/** Sudrash "bosish" emas, "sudrash" deb hisoblanadigan eng kichik masofa (px). */
const DRAG_THRESHOLD_PX = 6;

interface Props {
  children: ReactNode;
  /** Boshlang'ich holat (keyin foydalanuvchi sudrab o'zgartiradi). */
  initialSnap?: SheetSnap;
  /** Sarlavha qatorida ko'rsatiladigan ixtiyoriy element (masalan buyurtma holati). */
  header?: ReactNode;
}

/**
 * Xarita ustida turadigan, pastdan tepaga sudraladigan panel.
 *
 * `BottomSheetModal` dan farqi: u — modal dialog (fon qorayadi, tashqarisiga bosilsa
 * yopiladi), bu esa DOIMIY panel — yopilmaydi, faqat balandligi o'zgaradi va ostidagi
 * xarita bilan ishlashga xalaqit bermaydi.
 *
 * Sudrash `pointer` hodisalari bilan: bitta kod yo'li sensorli ekran uchun ham,
 * sichqoncha uchun ham ishlaydi (`touchstart` + `mousedown` juftligi shart emas).
 * Sudrash faqat tutqichdan boshlanadi — panel ichidagi ro'yxat odatdagidek
 * aylantiriladi (scroll), aks holda ikkalasi bir-biriga xalaqit berardi.
 */
export function BottomSheet({ children, initialSnap = 'half', header }: Props) {
  const [snap, setSnap] = useState<SheetSnap>(initialSnap);
  // Sudrash davomidagi joriy balandlik (px). `null` — sudralmayapti, balandlik
  // CSS o'tishi (transition) bilan snap nuqtasiga bog'langan.
  const [dragHeight, setDragHeight] = useState<number | null>(null);
  const dragState = useRef<{ startY: number; startHeight: number; moved: boolean } | null>(null);
  const sheetRef = useRef<HTMLDivElement>(null);

  const heightFor = useCallback(
    (value: SheetSnap) => Math.round(window.innerHeight * SNAP_RATIO[value]),
    [],
  );

  const nearestSnap = useCallback(
    (height: number): SheetSnap => {
      let best: SheetSnap = ORDER[0];
      let bestDistance = Infinity;
      for (const candidate of ORDER) {
        const distance = Math.abs(heightFor(candidate) - height);
        if (distance < bestDistance) {
          bestDistance = distance;
          best = candidate;
        }
      }
      return best;
    },
    [heightFor],
  );

  function handlePointerDown(event: React.PointerEvent<HTMLDivElement>) {
    const current = sheetRef.current?.getBoundingClientRect().height ?? heightFor(snap);
    dragState.current = { startY: event.clientY, startHeight: current, moved: false };
    // Barmoq tutqichdan chiqib ketsa ham hodisalar shu elementga kelaveradi.
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: React.PointerEvent<HTMLDivElement>) {
    const state = dragState.current;
    if (!state) return;
    // Yuqoriga sudrash => panel balandroq bo'ladi (shuning uchun ayirma teskari).
    const delta = state.startY - event.clientY;
    if (Math.abs(delta) > DRAG_THRESHOLD_PX) state.moved = true;
    const maxHeight = heightFor('full');
    const minHeight = heightFor('peek');
    setDragHeight(Math.min(maxHeight, Math.max(minHeight, state.startHeight + delta)));
  }

  function handlePointerUp(event: React.PointerEvent<HTMLDivElement>) {
    const state = dragState.current;
    dragState.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);

    if (!state) return;
    if (!state.moved) {
      // Sudralmadi — oddiy bosish: keyingi holatga o'tadi va oxiridan boshiga qaytadi.
      setDragHeight(null);
      setSnap((prev) => ORDER[(ORDER.indexOf(prev) + 1) % ORDER.length]);
      return;
    }
    const finalHeight = sheetRef.current?.getBoundingClientRect().height ?? heightFor(snap);
    setDragHeight(null);
    setSnap(nearestSnap(finalHeight));
  }

  // Ekran o'lchami o'zgarsa (burilish, klaviatura) balandlik snap nuqtasidan
  // hisoblanadi — `dragHeight` dagi eski piksel qiymati noto'g'ri bo'lib qolardi.
  useEffect(() => {
    function onResize() {
      setDragHeight(null);
    }
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const height = dragHeight ?? heightFor(snap);

  return (
    <div
      ref={sheetRef}
      className={styles.sheet}
      style={{
        height: `${height}px`,
        // Sudrash paytida animatsiya o'chiriladi — aks holda panel barmoqdan orqada qolardi.
        transition: dragHeight === null ? undefined : 'none',
      }}
    >
      <div
        className={styles.grabArea}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        role="button"
        tabIndex={0}
        aria-label="Panelni ko'tarish yoki tushirish"
        onKeyDown={(e) => {
          if (e.key === 'ArrowUp') {
            setSnap((prev) => ORDER[Math.min(ORDER.indexOf(prev) + 1, ORDER.length - 1)]);
          }
          if (e.key === 'ArrowDown') {
            setSnap((prev) => ORDER[Math.max(ORDER.indexOf(prev) - 1, 0)]);
          }
        }}
      >
        <div className={styles.dragHandle} />
        {header && <div className={styles.header}>{header}</div>}
      </div>

      <div className={styles.body}>{children}</div>
    </div>
  );
}
