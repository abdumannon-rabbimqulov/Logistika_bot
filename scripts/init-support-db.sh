#!/bin/bash
# Support mikroservizi uchun alohida baza yaratadi.
#
# Postgres image'i `/docker-entrypoint-initdb.d/` dagi skriptlarni FAQAT ma'lumot
# katalogi bo'sh bo'lganda (birinchi ishga tushishda) bajaradi. Ya'ni `postgres_data`
# volume'i allaqachon mavjud loyihada bu skript ishlamaydi — bunday holatda bazani
# qo'lda yaratish kerak:
#
#   docker compose exec db psql -U postgres -c "CREATE DATABASE support_db"
#
# Nega alohida baza: mikroserviz chegarasi. Support asosiy jadvallarni ko'rmasligi
# kerak — u bilan faqat RabbitMQ hodisalari orqali gaplashadi. Bitta Postgres
# konteynerida turishi lokal sinash uchun qulaylik, mantiqiy ajratishga ta'sir qilmaydi.
set -e

SUPPORT_DB_NAME="${SUPPORT_DB_NAME:-support_db}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE $SUPPORT_DB_NAME'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$SUPPORT_DB_NAME')\gexec
EOSQL

echo "init-support-db: '$SUPPORT_DB_NAME' bazasi tayyor"
