# Logistika_bot — kundalik docker buyruqlari uchun qisqartmalar.
#
#   make            — barcha buyruqlar ro'yxati
#   make fe         — faqat frontend (bir necha soniya)
#   make dev        — frontend + backend
#
# Bu fayl hech qanday sehr qilmaydi: har bir maqsad ostidagi `docker compose ...`
# buyrug'ini qo'lda ham yozish mumkin.

COMPOSE      := docker compose
COMPOSE_PROD := docker compose -f docker-compose.yml -f docker-compose.prod.yml
# Monitoring ATAYLAB alohida stack: ilova yiqilganda ham ishlab turishi kerak.
COMPOSE_MON  := docker compose -f docker-compose.monitoring.yml

.DEFAULT_GOAL := help
.PHONY: help fe dev up down logs ps fe-logs fe-restart fe-rebuild fe-install fe-add fe-shell fe-build fe-lint prod-up prod-down \
        worker-logs worker-restart worker-scale mq-ui support-logs support-ui support-db events-logs migrate test \
        mon-up mon-down mon-restart mon-ps mon-logs mon-collectors mon-alert-test mon-tunnel

help: ## Shu ro'yxatni ko'rsatadi
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ── Ishga tushirish ─────────────────────────────────────────────────────────

fe: ## Faqat frontend (Vite dev, :5173) — backendni kutmaydi
	$(COMPOSE) up -d frontend

dev: ## Frontend + backend (web osrm/db ni kutadi, frontend esa yo'q)
	$(COMPOSE) up -d frontend web

up: ## Butun stack (db, redis, osrm, web, bot, frontend)
	$(COMPOSE) up -d

down: ## Barcha konteynerlarni to'xtatish (volume'lar saqlanadi)
	$(COMPOSE) down

ps: ## Xizmatlar holati
	$(COMPOSE) ps

logs: ## Barcha loglar (Ctrl-C bilan chiqish)
	$(COMPOSE) logs -f

# ── Dispatch worker (RabbitMQ navbati) ──────────────────────────────────────

worker-logs: ## Haydovchi qidirish worker'ining loglari
	$(COMPOSE) logs -f dispatch-worker

worker-restart: ## Worker'ni qayta ishga tushirish
	$(COMPOSE) restart dispatch-worker

worker-scale: ## Worker'lar sonini o'zgartirish: make worker-scale n=3
	$(COMPOSE) up -d --scale dispatch-worker=$(n) dispatch-worker

mq-ui: ## RabbitMQ boshqaruv panelini brauzerda ochish (guest/guest)
	open http://localhost:15672

# ── Support mikroservizi va hodisalar ───────────────────────────────────────

support-logs: ## Support mikroservizi loglari
	$(COMPOSE) logs -f support

support-ui: ## Support Swagger UI (murojaatlar API si)
	open http://localhost:8010/docs

events-logs: ## Support hodisalarini adminlarga yetkazuvchi worker loglari
	$(COMPOSE) logs -f events-worker

support-db: ## Support bazasiga psql bilan kirish
	$(COMPOSE) exec db psql -U postgres -d support_db

# ── Migratsiya va testlar ───────────────────────────────────────────────────

migrate: ## Alembic migratsiyalarini qo'llash (manager roli shu yerda qo'shiladi)
	$(COMPOSE) exec web alembic upgrade head

test: ## Unit testlar (baza talab qilmaydi)
	$(COMPOSE) exec web pytest tests/ -q

# ── Frontend bilan ishlash ──────────────────────────────────────────────────

fe-logs: ## Frontend loglari
	$(COMPOSE) logs -f frontend

fe-restart: ## Frontend'ni qayta ishga tushirish
	$(COMPOSE) restart frontend

fe-rebuild: ## package.json / vite.config.ts / index.html o'zgargandan keyin (~10s)
	$(COMPOSE) up -d --build frontend

fe-install: ## Host'da bog'liqliklarni o'rnatish (IDE, tsc, lint uchun)
	cd Frontend && npm ci

fe-add: ## Paket qo'shish: make fe-add pkg=zod  (host'da o'rnatib, image'ni yangilaydi)
	@test -n "$(pkg)" || { echo "Foydalanish: make fe-add pkg=<paket-nomi>"; exit 1; }
	cd Frontend && npm install $(pkg)
	$(MAKE) fe-rebuild

fe-shell: ## Frontend konteyneri ichiga kirish
	$(COMPOSE) exec frontend sh

fe-build: ## Prod build'ni host'da sinash (tsc + vite build)
	cd Frontend && npm run build

fe-lint: ## oxlint (host'da)
	cd Frontend && npm run lint

# ── Ishlab chiqarish ────────────────────────────────────────────────────────

prod-up: ## Prod stack (frontend = nginx + statik dist, :8080)
	$(COMPOSE_PROD) up -d --build

prod-down: ## Prod stack'ni to'xtatish
	$(COMPOSE_PROD) down

# ── Monitoring (Netdata + Dockge) ───────────────────────────────────────────
#
# To'liq qo'llanma: docs/MONITORING.md
# Panellar faqat 127.0.0.1 da — serverdan foydalanish uchun `make mon-tunnel`.

mon-up: ## Monitoring stack (Netdata :19999 + Dockge :5002)
	@python3 monitoring/render-config.py
	$(COMPOSE_MON) up -d

mon-down: ## Monitoring stack'ni to'xtatish (metrikalar tarixi saqlanadi)
	$(COMPOSE_MON) down

mon-restart: ## Konfiguratsiyani qayta render qilib, Netdata'ni yangilash
	@python3 monitoring/render-config.py
	$(COMPOSE_MON) up -d --force-recreate netdata

mon-ps: ## Monitoring xizmatlari holati
	$(COMPOSE_MON) ps

mon-logs: ## Netdata loglari (kollektor xatolari shu yerda)
	$(COMPOSE_MON) logs -f netdata

mon-collectors: ## Qaysi kollektorlar ulandi / ulanmadi
	@docker exec logistika_netdata bash -c \
		'grep -E "(postgres|redis|rabbitmq|docker|httpcheck)" /var/log/netdata/collector.log | tail -30' \
		2>/dev/null || $(COMPOSE_MON) logs --tail=100 netdata | grep -iE "go.d|collector"

mon-alert-test: ## Telegram alert sozlamasini tekshirish (test xabari yuboradi)
	docker exec logistika_netdata /usr/libexec/netdata/plugins.d/alarm-notify.sh test

mon-tunnel: ## Serverdan panellarni ochish uchun SSH tunnel buyrug'ini ko'rsatadi
	@echo "Kompyuteringizda (serverda EMAS) shuni ishga tushiring:"
	@echo ""
	@echo "  ssh -N -L 19999:localhost:19999 -L 5002:localhost:5002 FOYDALANUVCHI@SERVER_IP"
	@echo ""
	@echo "So'ng brauzerda:"
	@echo "  Netdata → http://localhost:19999"
	@echo "  Dockge  → http://localhost:5002"
