#!/bin/bash

# 1. Dist fayllarni serverga yuborish
echo "Fayllar serverga yuborilmoqda..."
sshpass -p 'WeXw8VT3DO77iS5m0Hq6muT' scp -o StrictHostKeyChecking=no -r frontend/dist root@158.220.100.58:/tmp/dist

# 2. Serverga kirish va Nginx sozlash
echo "Server sozlamalari bajarilmoqda..."
sshpass -p 'WeXw8VT3DO77iS5m0Hq6muT' ssh -o StrictHostKeyChecking=no root@158.220.100.58 << 'EOF'
  # Nginx ni o'rnatish
  apt-get update
  apt-get install -y nginx

  # Papka yaratish va fayllarni joylash
  mkdir -p /var/www/logistic.org.uz
  rm -rf /var/www/logistic.org.uz/*
  mv /tmp/dist/* /var/www/logistic.org.uz/

  # Nginx konfiguratsiyasini yaratish
  cat > /etc/nginx/sites-available/logistic.org.uz << 'NGINX_CONF'
server {
    listen 80;
    server_name logistic.org.uz www.logistic.org.uz;

    root /var/www/logistic.org.uz;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINX_CONF

  # Konfiguratsiyani faollashtirish
  ln -sf /etc/nginx/sites-available/logistic.org.uz /etc/nginx/sites-enabled/
  
  # Nginx ni qayta ishga tushirish
  systemctl restart nginx
  
  echo "Muvaffaqiyatli yakunlandi! Endi logistic.org.uz saytiga kirib ko'ring."
EOF
