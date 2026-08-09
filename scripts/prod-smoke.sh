#!/usr/bin/env bash
# Ko'tarilgan prod stack'ni TASHQARIDAN — xuddi brauzer kabi — tekshiradi.
#
#   make prod-smoke                     # https://localhost (lokal sinov)
#   BASE=https://yuk.example.uz make prod-smoke   # serverda
#
# `-k` ataylab: lokal sinovda Caddy o'zining ichki CA'si bilan sertifikat beradi.
set -uo pipefail

BASE="${BASE:-https://localhost}"
CURL=(curl -sk --max-time 15)

# `docker-compose.prod.yml` DOMAIN'ni MAJBURIY talab qiladi (`${DOMAIN:?...}`).
# Serverda u `.env` dan keladi; lokal sinovda esa yo'q va `docker compose`
# buyruqlari xato bilan tugardi — natijada quyidagi tekshiruvlar jimgina
# "o'tgan" bo'lib ko'rinardi. Shuning uchun bu yerda zaxira qiymat beriladi.
export DOMAIN="${DOMAIN:-localhost}"
COMPOSE_PROD=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)

pass=0; fail=0
GRN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'

check() {
    local name="$1" expected="$2"; shift 2
    local got
    got="$("$@" 2>/dev/null)"
    if [ "$got" = "$expected" ]; then
        printf "  ${GRN}✓${NC} %-46s %s\n" "$name" "$got"
        pass=$((pass + 1))
    else
        printf "  ${RED}✗${NC} %-46s kutilgan=%s olindi=%s\n" "$name" "$expected" "${got:-JAVOB-YOQ}"
        fail=$((fail + 1))
    fi
}

status() { "${CURL[@]}" -o /dev/null -w '%{http_code}' "$1"; }

echo "Manzil: $BASE"
echo

echo "── Caddy / HTTPS ──"
check "HTTPS ishlaydi, SPA qaytadi"        "200" status "$BASE/"
check "HTTP → HTTPS ga yo'naltiriladi"     "308" status "$(printf '%s' "$BASE" | sed 's|^https|http|')/"

echo
echo "── Frontend nginx marshrutlari ──"
check "/api/health → backend (web:8000)"   "200" status "$BASE/api/health"
# Bu ikkisi ATAYLAB bor. nginx'da `proxy_pass` o'zgaruvchi bilan berilganda
# location prefiksini almashtirish mantig'i ISHLAMAYDI — `proxy_pass $web/api/;`
# deyilsa BARCHA so'rov backendga `/api/` bo'lib boradi. U holda `/api/health`
# ham 200 qaytaradi (`/api/` ning o'zi 200), ya'ni yuqoridagi tekshiruv xatoni
# sezmaydi. Mavjud bo'lmagan yo'l esa darhol ochib beradi: to'g'ri sozlanganda
# 404, buzilganda 200.
check "/api/ yo'llari to'liq uzatiladi"    "404" status "$BASE/api/__yoq__"
check "/static/ yo'llari to'liq uzatiladi" "404" status "$BASE/static/uploads/__yoq__.png"
check "SPA fallback (React Router yo'li)"  "200" status "$BASE/orders/1"

# Haqiqiy fayl: uploads volume + /static/ proxy zanjiri uchidan uchiga ishlaydimi.
if "${COMPOSE_PROD[@]}" exec -T web sh -c 'echo ok > /app/uploads/__smoke__.txt' 2>/dev/null; then
    check "yuklangan fayl HTTP orqali ochiladi" "200" status "$BASE/static/uploads/__smoke__.txt"
    "${COMPOSE_PROD[@]}" exec -T web rm -f /app/uploads/__smoke__.txt 2>/dev/null
else
    printf "  ${RED}✗${NC} %-46s konteynerga yozib bo'lmadi\n" "yuklangan fayl HTTP orqali ochiladi"
    fail=$((fail + 1))
fi

# WebSocket: Upgrade sarlavhalari backendga yetib boradimi. To'g'ri sozlanganda
# backend javob beradi (avtorizatsiyasiz 401/403), buzilganda so'rov umumiy
# `location /api/` ga tushib SPA index.html (200) qaytarardi.
ws_code="$("${CURL[@]}" -o /dev/null -w '%{http_code}' --http1.1 \
    -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
    -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
    "$BASE/api/drivers/ws/location")"
if [ "$ws_code" = "200" ]; then
    printf "  ${RED}✗${NC} %-46s WS backendga yetmadi (SPA qaytdi)\n" "WebSocket uzatiladi"
    fail=$((fail + 1))
else
    printf "  ${GRN}✓${NC} %-46s %s (backend javobi)\n" "WebSocket uzatiladi" "$ws_code"
    pass=$((pass + 1))
fi

echo
echo "── OSRM (tor va tezligi cheklangan yo'l) ──"
check "marshrut so'rovi ochiq" "Ok" \
    sh -c "curl -sk --max-time 20 '$BASE/osrm/route/v1/driving/69.24,41.31;69.28,41.33?overview=false' | sed -n 's/.*\"code\":\"\([A-Za-z]*\)\".*/\1/p'"
check "/osrm/table/... yopiq"              "404" status "$BASE/osrm/table/v1/driving/69.24,41.31;69.28,41.33"
check "/osrm/tile/... yopiq"               "404" status "$BASE/osrm/tile/v1/car/tile(1,1,1).mvt"

echo
echo "── Support mikroservizi ──"
# `/support/...` SPA index.html emas, support konteyneridan javob kelishi kerak.
# Mavjud yo'l tanlangan: 401 "avtorizatsiya kerak" — ya'ni so'rov haqiqiy
# endpoint'ga yetib bordi. 404 kelsa yo'l to'liq uzatilmayapti, 200 (HTML)
# kelsa umuman support'ga bormay SPA fallback'ga tushgan.
check "/support/tickets → support konteyneri" "401" status "$BASE/support/tickets"
check "/support/ mavjud bo'lmagan yo'l"       "404" status "$BASE/support/__yoq__"

echo
echo "── Ochiq portlar (faqat 80/443 bo'lishi kerak) ──"
ps_json="$("${COMPOSE_PROD[@]}" ps --format json 2>/dev/null || true)"
if [ -z "$ps_json" ]; then
    # Bo'sh chiqishni "port ochiq emas" deb o'qish MUMKIN EMAS — bu tekshiruvning
    # butun ma'nosini yo'qotadi (aynan shu xato bir marta yolg'on "✓" bergan).
    printf "  ${RED}✗${NC} 'docker compose ps' javob bermadi — port tekshiruvi bajarilmadi\n"
    fail=$((fail + 1))
else
    open_ports="$(printf '%s' "$ps_json" | tr ',' '\n' | grep -o '0\.0\.0\.0:[0-9]*' | sort -u | tr '\n' ' ')"
    echo "  0.0.0.0 ga bog'langan: ${open_ports:-YOQ}"
    if printf '%s' "$open_ports" | grep -qE '0\.0\.0\.0:(5432|5433|6380|5672|15672|5001|8003|8010)'; then
        printf "  ${RED}✗${NC} Ichki xizmat porti tashqariga ochiq!\n"
        fail=$((fail + 1))
    elif ! printf '%s' "$open_ports" | grep -q '0\.0\.0\.0:443'; then
        printf "  ${RED}✗${NC} Caddy 443-portni ochmagan\n"
        fail=$((fail + 1))
    else
        printf "  ${GRN}✓${NC} Faqat 80/443 ochiq, ichki xizmatlar yopiq\n"
        pass=$((pass + 1))
    fi
fi

echo
echo "── Migratsiya ──"
alembic_rev="$("${COMPOSE_PROD[@]}" exec -T db \
    psql -U "${DB_USER:-postgres}" -d "${DB_NAME:-logistika_db}" -tAc \
    'select version_num from alembic_version' 2>/dev/null | tr -d '[:space:]')"
if [ -n "$alembic_rev" ]; then
    printf "  ${GRN}✓${NC} alembic_version = %s\n" "$alembic_rev"
    pass=$((pass + 1))
else
    printf "  ${RED}✗${NC} alembic_version bo'sh — migratsiya bajarilmagan\n"
    fail=$((fail + 1))
fi

echo
echo "─────────────────────────────"
printf "O'tdi: %d   Yiqildi: %d\n" "$pass" "$fail"
[ "$fail" -eq 0 ]
