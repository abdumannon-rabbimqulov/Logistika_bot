#!/bin/bash

# Sozlamalar
SERVER="root@158.220.100.58"
SSH_KEY="$HOME/.ssh/deploy_key"
APP_DIR="/root/logistika_bot"
ARCHIVE_NAME="logistika_bot.tar.gz"

# Ranglar
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🚀 Deployment boshlandi...${NC}"

# 1. Loyihani arxivlash
echo -e "${CYAN}📦 Loyihani arxivlash...${NC}"
tar --exclude='.venv' --exclude='__pycache__' --exclude='.git' --exclude='*.tar.gz' --exclude='.idea' -czf $ARCHIVE_NAME .

# 2. Serverga yuklash
echo -e "${CYAN}📤 Serverga yuborilmoqda...${NC}"
scp -i $SSH_KEY -o StrictHostKeyChecking=no $ARCHIVE_NAME $SERVER:$APP_DIR/

# 3. Serverda yangilash
echo -e "${CYAN}🔄 Serverda konteynerlarni yangilash...${NC}"
ssh -i $SSH_KEY -o StrictHostKeyChecking=no $SERVER << EOF
    cd $APP_DIR
    tar -xzf $ARCHIVE_NAME
    rm $ARCHIVE_NAME
    
    # Portni 8003 da qolishini ta'minlash
    sed -i 's/"8000:8000"/"8003:8000"/g' docker-compose.yml
    
    docker-compose up -d --build
    docker image prune -f
EOF

# 4. Tozalash
rm $ARCHIVE_NAME

echo -e "${GREEN}✅ Deployment muvaffaqiyatli yakunlandi!${NC}"
echo -e "${GREEN}Web: https://logistic.org.uz${NC}"
echo -e "${GREEN}Swagger: https://logistic.org.uz/docs${NC}"
