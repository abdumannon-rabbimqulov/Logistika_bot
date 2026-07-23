import math
from typing import Optional, Sequence

# Yer radiusi (km) — bir gradus kenglik ~111.32 km
_KM_PER_DEGREE = 111.32


def simplify_polyline(
    points: Sequence[tuple[float, float]], tolerance_m: float = 15.0
) -> list[tuple[float, float]]:
    """Douglas-Peucker: chiziq shaklini saqlagan holda ortiqcha nuqtalarni olib tashlaydi.

    OSRM `overview=full` juda ko'p nuqta qaytaradi (300 km yo'l uchun ~3000 ta, ~68 KB JSON).
    `overview=simplified` esa aksincha juda qo'pol (shahar ichidagi 7 km yo'l uchun atigi
    20 ta nuqta — burilishlarni "kesib" o'tadi). Shuning uchun to'liq geometriya olinib,
    shu yerda ko'rsatish uchun yetarli aniqlikda soddalashtiriladi: qisqa marshrutlar
    tafsilotini yo'qotmaydi, uzunlari esa keraksiz nuqtalardan tozalanadi.

    points: [(latitude, longitude), ...]. tolerance_m: chiziqdan ruxsat etilgan maksimal
    og'ish (metr) — undan kam og'adigan nuqtalar tashlab yuboriladi.
    """
    if len(points) <= 2:
        return list(points)

    # Gradusni taxminan metrga o'tkazish uchun masshtab. Uzunlik gradusi qutbga
    # yaqinlashgan sari qisqaradi, shuning uchun o'rtacha kenglik bo'yicha cos() olinadi.
    mean_lat = sum(lat for lat, _ in points) / len(points)
    lat_scale = _KM_PER_DEGREE * 1000
    lon_scale = lat_scale * math.cos(math.radians(mean_lat))
    tolerance_sq = tolerance_m ** 2

    def _perpendicular_distance_sq(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        """p nuqtaning a-b kesmasigacha bo'lgan masofasi kvadrati (metrda)."""
        px, py = (p[1] - a[1]) * lon_scale, (p[0] - a[0]) * lat_scale
        bx, by = (b[1] - a[1]) * lon_scale, (b[0] - a[0]) * lat_scale
        seg_len_sq = bx * bx + by * by
        if seg_len_sq == 0:  # a va b ustma-ust — oddiy nuqtalar orasidagi masofa
            return px * px + py * py
        # Proyeksiyani [0, 1] oralig'iga qisish — kesmadan tashqariga chiqmasligi uchun
        t = max(0.0, min(1.0, (px * bx + py * by) / seg_len_sq))
        dx, dy = px - t * bx, py - t * by
        return dx * dx + dy * dy

    # Rekursiv emas, stack orqali — juda uzun marshrutlarda rekursiya chuqurligi oshib
    # ketmasligi uchun. keep[i] = shu nuqta natijada qoladimi.
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        if end - start < 2:
            continue
        max_dist_sq, max_index = -1.0, start
        for i in range(start + 1, end):
            dist_sq = _perpendicular_distance_sq(points[i], points[start], points[end])
            if dist_sq > max_dist_sq:
                max_dist_sq, max_index = dist_sq, i
        if max_dist_sq > tolerance_sq:
            keep[max_index] = True
            stack.append((start, max_index))
            stack.append((max_index, end))

    return [p for p, keep_it in zip(points, keep) if keep_it]


def calculate_distance_km(lat1: Optional[float], lon1: Optional[float], lat2: Optional[float], lon2: Optional[float]) -> Optional[float]:
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees) using haversine formula.
    Returns None if any of the coordinates is None.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None

    # Convert decimal degrees to radians 
    lon1_rad, lat1_rad, lon2_rad, lat2_rad = map(math.radians, [lon1, lat1, lon2, lat2])

    # Haversine formula 
    dlon = lon2_rad - lon1_rad 
    dlat = lat2_rad - lat1_rad 
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers
    return c * r
