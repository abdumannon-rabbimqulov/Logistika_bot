#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

LOGISTIKA_SSH_HOST="${LOGISTIKA_SSH_HOST:-root@158.220.100.58}"
SSH_KEY="${LOGISTIKA_SSH_KEY:-$HOME/.ssh/deploy_key}"
REMOTE_PROJECT_DIR="/root/Logistika_bot"

if [ ! -f "$SSH_KEY" ]; then
    echo "SSH kalit yo‘q: $SSH_KEY" >&2
    exit 1
fi

SSH_BASE=(
    ssh
    -i "$SSH_KEY"
    -o StrictHostKeyChecking=no
    -o ControlMaster=auto
    -o ControlPersist=60s
    -o ControlPath="/tmp/logistika_full_%r@%h:%p"
)

echo "🚀 Deploying backend + frontend (Docker)..."

echo "📤 Syncing project to ${LOGISTIKA_SSH_HOST}:${REMOTE_PROJECT_DIR}..."
# Create directory on server
"${SSH_BASE[@]}" "$LOGISTIKA_SSH_HOST" "mkdir -p '$REMOTE_PROJECT_DIR'"

# 2. Rsync the whole project (excluding unnecessary things via --exclude)
rsync -az --delete \
    -e "ssh -i '$SSH_KEY' -o StrictHostKeyChecking=no -o ControlMaster=auto -o ControlPersist=60s -o ControlPath=/tmp/logistika_full_%r@%h:%p" \
    --exclude '.git' \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude 'Frontend_bot/admin/node_modules' \
    --exclude 'Frontend_bot/node_modules' \
    --exclude '.cursor' \
    --exclude 'terminals' \
    --exclude '.DS_Store' \
    --exclude '._*' \
    ./ \
    "$LOGISTIKA_SSH_HOST:$REMOTE_PROJECT_DIR/"

echo "⚙️  Restarting Docker containers and Nginx on server..."
"${SSH_BASE[@]}" "$LOGISTIKA_SSH_HOST" bash << REMOTE
set -euo pipefail

# Update Nginx config
install -m 0644 "$REMOTE_PROJECT_DIR/Frontend_bot/nginx/logistic-org-uz.vps.conf" /etc/nginx/conf.d/logistic.org.uz.conf
nginx -t
systemctl reload nginx

# Rebuild and restart docker compose services
cd "$REMOTE_PROJECT_DIR"
docker compose up -d --build backend-api backend-bot frontend-bot migrations

REMOTE

echo "✅ Full Deploy successfully completed!"
