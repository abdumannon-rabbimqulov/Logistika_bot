#!/usr/bin/env bash
#
# OSRM xaritasini yangilaydi: Geofabrik'dan O'zbekiston ekstraktini yuklab oladi,
# marshrut grafigini qayta hisoblaydi va ishlab turgan OSRM'ni yangisiga o'tkazadi.
#
#   ./scripts/update-osrm-map.sh
#
# Nima uchun kerak: OSRM yo'l tarmog'ini oldindan "kompilyatsiya" qilib qo'yadi
# (.osrm.* fayllar). Yangi yo'l qurilsa yoki OSM'da tuzatish bo'lsa, u avtomatik
# yangilanmaydi — shu skriptni qayta ishga tushirish kerak.
#
# Qanchalik tez-tez? Yo'l tarmog'i sekin o'zgaradi — 1-3 oyda bir marta yetarli.
# Qayta hisoblash Apple Silicon'da emulyatsiya (linux/amd64) ostida ishlagani uchun
# ancha sekin va bir necha GB RAM talab qiladi, shuning uchun uni tez-tez qilish shart emas.
#
# Eski ma'lumot jarayon oxirigacha o'z ishini davom ettiraveradi — almashtirish faqat
# yangisi to'liq va muvaffaqiyatli tayyor bo'lgandan keyin, konteyner qayta ishga
# tushirilgan paytda sodir bo'ladi (bir necha soniya uzilish).

set -euo pipefail

REGION_URL="https://download.geofabrik.de/asia/uzbekistan-latest.osm.pbf"
IMAGE="osrm/osrm-backend"
PLATFORM="linux/amd64"        # docker-compose.yml dagi bilan bir xil bo'lishi shart
PROFILE="/opt/car.lua"        # yuk mashinasi profili kerak bo'lsa: /opt/truck.lua

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$REPO_ROOT/osrm-data"
BUILD_DIR="$DATA_DIR/.build"
NAME="uzbekistan"             # docker-compose.yml `/data/uzbekistan.osrm` kutadi

log() { printf '\n\033[1;32m==>\033[0m %s\n' "$1"; }
die() { printf '\n\033[1;31mXATO:\033[0m %s\n' "$1" >&2; exit 1; }

command -v docker >/dev/null || die "docker topilmadi"
docker info >/dev/null 2>&1 || die "Docker ishga tushmagan — Docker Desktop'ni oching"

# Qayta ishlash vaqtinchalik papkada boradi: yarim yo'lda uzilib qolsa ham
# ishlab turgan xarita buzilmaydi.
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
trap 'rm -rf "$BUILD_DIR"' EXIT

log "1/5 Geofabrik'dan yuklab olinmoqda"
# -L: redirect (uzbekistan-latest -> uzbekistan-YYMMDD) kuzatiladi
curl -fL --progress-bar -o "$BUILD_DIR/$NAME.osm.pbf" "$REGION_URL" \
  || die "Yuklab bo'lmadi — internet aloqasini tekshiring"

SNAPSHOT="$(curl -fsSLI "$REGION_URL" | tr -d '\r' \
  | awk 'tolower($1) == "last-modified:" { $1 = ""; sub(/^ /, ""); print }' | tail -1)"
SIZE="$(du -h "$BUILD_DIR/$NAME.osm.pbf" | cut -f1)"
log "Yuklandi: $SIZE${SNAPSHOT:+, sana: $SNAPSHOT}"

# osrm-extract juda ko'p RAM yeydi; --memory bermaymiz, Docker Desktop limitidan foydalanadi.
osrm() {
  docker run --rm --platform "$PLATFORM" -v "$BUILD_DIR:/data" "$IMAGE" "$@"
}

log "2/5 osrm-extract (yo'l tarmog'ini ajratish — eng uzun bosqich)"
osrm osrm-extract -p "$PROFILE" "/data/$NAME.osm.pbf" || die "osrm-extract yiqildi (ko'pincha RAM yetmaydi — Docker Desktop'da xotira limitini oshiring)"

log "3/5 osrm-partition (grafikni bo'laklarga bo'lish)"
osrm osrm-partition "/data/$NAME.osrm" || die "osrm-partition yiqildi"

log "4/5 osrm-customize (og'irliklarni hisoblash)"
osrm osrm-customize "/data/$NAME.osrm" || die "osrm-customize yiqildi"

[ -f "$BUILD_DIR/$NAME.osrm.mldgr" ] || die "Kutilgan natija fayllari yaratilmadi"

log "5/5 Yangi xaritaga o'tkazilmoqda"
# Konteyner fayllarni ochiq ushlab turgani uchun avval to'xtatiladi.
docker compose --project-directory "$REPO_ROOT" stop osrm >/dev/null 2>&1 || true

find "$DATA_DIR" -maxdepth 1 -name "$NAME.osrm*" -delete
find "$DATA_DIR" -maxdepth 1 -name "$NAME.osm.pbf" -delete
mv "$BUILD_DIR/$NAME".* "$DATA_DIR/"

cat > "$DATA_DIR/VERSION" <<EOF
source: $REGION_URL
snapshot: ${SNAPSHOT:-noma'lum}
processed: $(date +%Y-%m-%d)
algorithm: mld
profile: $PROFILE
EOF

docker compose --project-directory "$REPO_ROOT" up -d osrm >/dev/null

log "Tayyor. Yangi xarita: $(du -sh "$DATA_DIR" | cut -f1)"
cat "$DATA_DIR/VERSION"

# Haqiqiy so'rov bilan tekshirish (Toshkent -> Samarqand)
log "Tekshirilmoqda..."
for _ in $(seq 20); do
  if curl -fsS --max-time 3 "http://localhost:5001/route/v1/driving/69.240562,41.311081;66.975463,39.654935?overview=false" 2>/dev/null \
     | grep -q '"code":"Ok"'; then
    printf '\033[1;32mOSRM ishlayapti ✓\033[0m\n'
    exit 0
  fi
  sleep 2
done
die "OSRM javob bermadi — 'docker compose logs osrm' bilan tekshiring"
