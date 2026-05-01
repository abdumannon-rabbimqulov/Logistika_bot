# 🔒 Logistika Bot - Environment Setup Guide

## ⚠️ SECURITY FIRST!

This project requires sensitive environment variables (API keys, database passwords, etc.). **NEVER commit `.env` to Git!**

---

## 📝 Step 1: Create Your `.env` File

1. Copy the template:
```bash
cp .env.example .env
```

2. Edit `.env` and replace placeholder values with real credentials

---

## 🔑 Environment Variables Reference

### **Telegram Bot**
- `BOT_TOKEN` - Get from BotFather (@BotFather on Telegram)
  - Format: `1234567890:ABCDefGHIjklmnoPQRStuvWXYZ123456789`

### **Google Gemini AI**
- `API_KEY` - Get from Google Cloud Console
  - https://aistudio.google.com/apikey
  - Format: `AIzaSy...` (long string)

### **Database**
- `DB_URL` - PostgreSQL connection string
  - Format: `postgresql+asyncpg://username:password@host:port/database`
  - Example: `postgresql+asyncpg://postgres:mypassword@localhost:5432/logistika_db`
  - For production: Use strong password (50+ random chars)

### **Email (Gmail)**
- `EMAIL_USERNAME` - Gmail address
- `EMAIL_PASSWORD` - **App-specific password** (NOT your Gmail password!)
  - Generate: https://myaccount.google.com/apppasswords
  - Requires 2FA enabled on Gmail account

### **JWT Security**
- `SECRET_KEY` - Random secret for JWT tokens
  - Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
  - Minimum 32 characters
  - **NEVER share this key!**
- `ALGORITHM` - Usually `HS256` (don't change)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token validity (default: 60)
- `REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token validity (default: 1)

### **Admin**
- `ADMIN` - Comma-separated list of admin Telegram user IDs
  - Get your ID: Send `/start` to @userinfobot
  - Format: `123456789,987654321`

### **Other**
- `WEBAPP_URL` - Your application URL
  - Local: `http://localhost:8000`
  - Production: `https://yourdomain.com`

---

## 🚀 Local Development Setup

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start PostgreSQL
```bash
# Using Docker
docker run --name logistika_db -e POSTGRES_PASSWORD=2103 -p 5432:5432 -d postgres:15

# Or use local PostgreSQL
# Make sure it's running on localhost:5432
```

### 3. Run Database Migrations
```bash
alembic upgrade head
```

### 4. Start the Bot
```bash
python main.py
```

---

## 🐳 Docker Setup

### 1. Build & Run with Docker Compose
```bash
docker-compose up --build
```

### 2. Environment Variables for Docker
Create `.env.docker` with the same variables:
```dotenv
BOT_TOKEN=your_token
API_KEY=your_key
# ... etc
```

Or pass via environment:
```bash
docker run -e BOT_TOKEN=xxx -e DB_URL=postgresql://... logistika_bot
```

---

## ✅ Test Your Configuration

### 1. Check if .env is properly loaded:
```python
from config.config import BOT_TOKEN, API_KEY, SECRET_KEY
print(f"✅ BOT_TOKEN: {BOT_TOKEN[:20]}...")  # Don't print full token
print(f"✅ API_KEY loaded: {bool(API_KEY)}")
print(f"✅ SECRET_KEY loaded: {bool(SECRET_KEY)}")
```

### 2. Test database connection:
```bash
python -c "
import asyncio
from config.config import engine
from users.models import User

async def test():
    async with engine.begin() as conn:
        print('✅ Database connection successful!')
        
asyncio.run(test())
"
```

### 3. Test bot token:
```bash
python -c "
from config.config import BOT_TOKEN
from aiogram import Bot

async def test():
    bot = Bot(token=BOT_TOKEN)
    me = await bot.get_me()
    print(f'✅ Bot connected: {me.username}')
    
import asyncio
asyncio.run(test())
"
```

---

## 🔐 Production Security Checklist

- [ ] Are all tokens/passwords strong (50+ random characters)?
- [ ] Is `.env` in `.gitignore`? (`grep .env .gitignore`)
- [ ] Database password is NOT default?
- [ ] Gmail 2FA is enabled + app-specific password used?
- [ ] `SECRET_KEY` is unique and never shared?
- [ ] `ENVIRONMENT=production` is set?
- [ ] All required env vars present? (Check error logs on startup)
- [ ] Log level set to `INFO` (not `DEBUG`)?
- [ ] Database backups configured?
- [ ] HTTPS/TLS enabled in production?

---

## 🆘 Troubleshooting

### `ValueError: Environment variable 'BOT_TOKEN' is not set`
✅ Solution: Check `.env` file exists and contains `BOT_TOKEN=...`

### `No module named 'google'`
✅ Solution: `pip install google-generativeai`

### Database connection refused
✅ Solution: Make sure PostgreSQL is running on `DB_HOST:DB_PORT`

### Gmail password not working
✅ Solution: Use app-specific password, not Gmail password
- Remove 2FA temporarily, set app password, re-enable 2FA

### Telegram webhook errors
✅ Solution: `WEBAPP_URL` must be HTTPS and publicly accessible

---

## 📚 Resources

- [Telegram BotFather](https://t.me/BotFather)
- [Google AI Studio](https://aistudio.google.com)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Gmail App Passwords](https://myaccount.google.com/apppasswords)
- [Python Secrets](https://docs.python.org/3/library/secrets.html)

---

**Remember: Never share your `.env` file or its contents!** 🔐

