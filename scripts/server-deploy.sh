#!/usr/bin/env bash
# Serverda deploy / yangilash. Idempotent — xohlagancha qayta ishga tushirish mumkin.
#
#   ./scripts/server-deploy.sh          — git pull + build + up
#   ./scripts/server-deploy.sh --no-pull  — kodni tortmasdan (lokal sinov uchun)
#
# Nomi ataylab `deploy.sh` EMAS: `.gitignore` da `deploy.sh` qatori bor va u
# (slashsiz naqsh bo'lgani uchun) istalgan papkadagi shu nomli faylni yashiradi.
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)

RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[0;33m'; NC='\033[0m'
say()  { printf "${GRN}==>${NC} %s\n" "$*"; }
warn() { printf "${YLW}!!${NC}  %s\n" "$*"; }
die()  { printf "${RED}XATO:${NC} %s\n" "$*" >&2; exit 1; }

PULL=1
[ "${1:-}" = "--no-pull" ] && PULL=0

# ── 1. Old shartlar ─────────────────────────────────────────────────────────
command -v docker >/dev/null || die "docker o'rnatilmagan. docs/DEPLOY.md ga qarang."
docker compose version >/dev/null 2>&1 || die "'docker compose' (v2) topilmadi."

[ -f "$ROOT/.env" ] || die ".env fayli yo'q. Namuna: cp .env.example .env && nano .env"

# .env dagi majburiy o'zgaruvchilar. Qiymatlar EKRANGA CHIQARILMAYDI — faqat
# bo'sh yoki namunaviy qoldirilganlari aytiladi.
missing=()
placeholder=()
check_env() {
    local name="$1"
    local value
    # `.env` ni source qilmaymiz: ichida tirnoqsiz maxsus belgilar bo'lishi mumkin.
    value="$(grep -E "^${name}=" "$ROOT/.env" | tail -n1 | cut -d= -f2- || true)"
    if [ -z "$value" ]; then
        missing+=("$name")
    elif printf '%s' "$value" | grep -qiE 'change_me|your_|example\.(org|uz|com)'; then
        placeholder+=("$name")
    fi
}
for v in BOT_TOKEN SECRET_KEY DB_PASSWORD DB_URL DOMAIN WEBAPP_URL; do check_env "$v"; done

[ ${#missing[@]} -eq 0 ] || die ".env da to'ldirilmagan: ${missing[*]}"
if [ ${#placeholder[@]} -gt 0 ]; then
    die ".env da hali namunaviy qiymat turibdi: ${placeholder[*]} — haqiqiysiga almashtiring."
fi

# WEBAPP_URL https bo'lmasa Telegram Mini App menyu tugmasi umuman qo'yilmaydi
# (main.py `_setup_menu_button`). Bu jimgina o'tib ketadigan xato, shuning uchun
# deploy'ni to'xtatamiz.
webapp_url="$(grep -E '^WEBAPP_URL=' "$ROOT/.env" | tail -n1 | cut -d= -f2-)"
case "$webapp_url" in
    https://*) ;;
    *) die "WEBAPP_URL https:// bilan boshlanishi shart (hozir: $webapp_url)" ;;
esac

# ── 2. OSRM xaritasi ────────────────────────────────────────────────────────
# ~1 GB, git'da saqlanmaydi. Busiz `osrm` konteyneri healthcheck'dan o'tmaydi va
# web/bot/dispatch-worker (`service_healthy` kutadi) umuman ishga tushmaydi.
if [ ! -f "$ROOT/osrm-data/uzbekistan.osrm" ]; then
    die "osrm-data/uzbekistan.osrm topilmadi. Avval xaritani tayyorlang:
    ./scripts/update-osrm-map.sh
  (~1 GB yuklab olinadi va qayta ishlanadi — birinchi marta uzoq davom etadi)"
fi

# ── 3. Kodni yangilash ──────────────────────────────────────────────────────
if [ "$PULL" = "1" ] && [ -d "$ROOT/.git" ]; then
    say "Kod yangilanmoqda (git pull)..."
    git pull --ff-only
fi

PREV_IMAGE="$(docker image inspect logistika_backend:latest --format '{{.Id}}' 2>/dev/null || echo '-')"

# ── 4. Build va ishga tushirish ─────────────────────────────────────────────
say "Image'lar yig'ilmoqda..."
"${COMPOSE[@]}" build

say "Xizmatlar ishga tushirilmoqda..."
# `--remove-orphans` — eski nomdagi konteynerlar (masalan avvalgi prod nomlari)
# qolib ketmasin.
"${COMPOSE[@]}" up -d --remove-orphans

# ── 5. Sog'liqni kutish ─────────────────────────────────────────────────────
say "Xizmatlar tayyor bo'lishi kutilmoqda..."
deadline=$(( $(date +%s) + 300 ))
while :; do
    unhealthy="$("${COMPOSE[@]}" ps --format '{{.Service}} {{.State}} {{.Health}}' 2>/dev/null \
        | awk '$3 != "" && $3 != "healthy" { print $1 }' || true)"
    stopped="$("${COMPOSE[@]}" ps --format '{{.Service}} {{.State}}' 2>/dev/null \
        | awk '$2 != "running" && $1 != "migrate" { print $1 }' || true)"
    if [ -z "$unhealthy" ] && [ -z "$stopped" ]; then
        break
    fi
    if [ "$(date +%s)" -ge "$deadline" ]; then
        warn "5 daqiqada hamma xizmat tayyor bo'lmadi. Holat:"
        "${COMPOSE[@]}" ps
        warn "Loglar:  docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=50"
        exit 1
    fi
    sleep 5
done

# ── 6. Tekshiruv ────────────────────────────────────────────────────────────
say "Backend /health tekshirilmoqda..."
"${COMPOSE[@]}" exec -T web curl -fsS http://127.0.0.1:8000/health >/dev/null \
    && say "Backend javob bermoqda." \
    || die "Backend /health javob bermadi."

domain="$(grep -E '^DOMAIN=' "$ROOT/.env" | tail -n1 | cut -d= -f2-)"
say "Tayyor: https://${domain}"

# ── 7. Tozalash ─────────────────────────────────────────────────────────────
# Faqat hech qaysi konteyner ishlatmayotgan "osilib qolgan" qatlamlar.
docker image prune -f >/dev/null 2>&1 || true

if [ "$PREV_IMAGE" != "-" ]; then
    echo
    warn "Rollback kerak bo'lsa oldingi backend image: ${PREV_IMAGE:7:12}"
    warn "  docker tag ${PREV_IMAGE} logistika_backend:latest && \\"
    warn "  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-build"
fi
