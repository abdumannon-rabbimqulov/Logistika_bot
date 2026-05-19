#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

LOGISTIKA_SSH_HOST="${LOGISTIKA_SSH_HOST:-root@158.220.100.58}"
SSH_KEY="${LOGISTIKA_SSH_KEY:-$HOME/.ssh/deploy_key}"
REMOTE_PROJECT_DIR="${LOGISTIKA_REMOTE_PROJECT_DIR:-/root/Logistika_bot}"

deploy_here() {
    local project_dir="${1:-$(pwd)}"

    if [ ! -f "$project_dir/.env" ]; then
        echo ".env topilmadi: $project_dir/.env" >&2
        echo "Avval .env.example dan .env yarating va secretlarni to'ldiring." >&2
        exit 1
    fi

    if [ "${LOGISTIKA_APPLY_NGINX:-0}" = "1" ]; then
        if [ ! -f "$project_dir/logistic.org.uz.conf" ]; then
            echo "Nginx config topilmadi: $project_dir/logistic.org.uz.conf" >&2
            exit 1
        fi

        echo "⚙️  Applying backend Nginx config..."
        if [ "$(id -u)" -eq 0 ]; then
            install -m 0644 "$project_dir/logistic.org.uz.conf" /etc/nginx/conf.d/logistic.org.uz.conf
            nginx -t
            systemctl reload nginx
        elif command -v sudo >/dev/null 2>&1; then
            sudo install -m 0644 "$project_dir/logistic.org.uz.conf" /etc/nginx/conf.d/logistic.org.uz.conf
            sudo nginx -t
            sudo systemctl reload nginx
        else
            echo "sudo topilmadi; Nginx config qo'lda yangilanishi kerak." >&2
            exit 1
        fi
    else
        echo "⚙️  Skipping Nginx config (frontend repo owns public Nginx)."
    fi

    echo "🕐 Setting timezone to Asia/Tashkent..."
    if command -v timedatectl >/dev/null 2>&1; then
        if [ "$(id -u)" -eq 0 ]; then
            timedatectl set-timezone Asia/Tashkent
        else
            sudo timedatectl set-timezone Asia/Tashkent
        fi
    else
        if [ "$(id -u)" -eq 0 ]; then
            ln -snf /usr/share/zoneinfo/Asia/Tashkent /etc/localtime
            echo Asia/Tashkent > /etc/timezone
        else
            sudo ln -snf /usr/share/zoneinfo/Asia/Tashkent /etc/localtime
            echo Asia/Tashkent | sudo tee /etc/timezone >/dev/null
        fi
    fi

    echo "🐳 Building and restarting Docker services..."
    cd "$project_dir"
    docker compose up -d --build db logistika-redis migrations backend-api backend-bot
}

if [ "${LOGISTIKA_DEPLOY_LOCAL:-0}" = "1" ] || [ ! -f "$SSH_KEY" ]; then
    echo "🚀 Deploying locally from $(pwd)..."
    deploy_here "$(pwd)"
else
    # Clean any stale ControlMaster sockets from previous runs
    rm -f /tmp/logistika_full_* 2>/dev/null || true

    SSH_BASE=(
        ssh
        -i "$SSH_KEY"
        -o StrictHostKeyChecking=no
        -o BatchMode=yes
        -o ConnectTimeout=45
        -o ServerAliveInterval=15
        -o ServerAliveCountMax=4
        -o ControlMaster=no
    )

    echo "🚀 Deploying to ${LOGISTIKA_SSH_HOST}..."
    echo "📤 Syncing project to ${REMOTE_PROJECT_DIR}..."

    "${SSH_BASE[@]}" "$LOGISTIKA_SSH_HOST" "mkdir -p '$REMOTE_PROJECT_DIR'"

    rsync -az --delete \
        -e "ssh -i '$SSH_KEY' -o StrictHostKeyChecking=no -o ControlMaster=auto -o ControlPersist=60s -o ControlPath=/tmp/logistika_full_%r@%h:%p" \
        --exclude '.git' \
        --exclude 'venv' \
        --exclude '__pycache__' \
        --exclude 'Frontend_bot' \
        --exclude '.cursor' \
        --exclude 'terminals' \
        --exclude '.DS_Store' \
        --exclude '._*' \
        ./ \
        "$LOGISTIKA_SSH_HOST:$REMOTE_PROJECT_DIR/"

    echo "⚙️  Running deploy on server..."
    "${SSH_BASE[@]}" "$LOGISTIKA_SSH_HOST" "cd '$REMOTE_PROJECT_DIR' && LOGISTIKA_DEPLOY_LOCAL=1 bash deploy-all.sh"
fi

echo "✅ Backend Docker deploy successfully completed!"
echo "   API: https://logistic.org.uz/health"
echo "   Nginx: frontend repo boshqaradi. Backend nginx kerak bo'lsa LOGISTIKA_APPLY_NGINX=1 ishlating."
