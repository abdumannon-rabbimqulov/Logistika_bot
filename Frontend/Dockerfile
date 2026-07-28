# ── Build bosqichi ──────────────────────────────────────────────────────────
# Node 22: vite@8, @vitejs/plugin-react@6 va oxlint@1 `engines: node ^20.19.0 || >=22.12.0`
# talab qiladi, Node 20 esa qo'llab-quvvatlash muddatini tugatgan (EOL).
FROM node:22-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Vite env o'zgaruvchilari build vaqtida JS bundle'ga "quyiladi" (runtime'da emas) —
# shuning uchun build-arg sifatida qabul qilinadi (docker-compose.yml'dagi `args:` ga qarang).
ARG VITE_API_BASE_URL=http://localhost:8000/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# ── Serve bosqichi ──────────────────────────────────────────────────────────
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
