"""
Email OTP Service
─────────────────────────────────────────────────────────────────
Bu modul foydalanuvchi ro'yxatdan o'tishida email ga
tasdiqlash kodi (OTP) yuborish uchun ishlatiladi.

Ishlash tartibi:
  1. /register  → email, parol, to'liq ism qabul qilinadi
  2. 6 xonali OTP yaratiladi va Redis/xotiraga saqlanadi
  3. Email ga HTML xat yuboriladi
  4. /verify-email → OTP tekshiriladi va foydalanuvchi yaratiladi

Sozlash uchun .env ga quyidagilarni yozing:
  EMAIL_HOST     = smtp.gmail.com
  EMAIL_PORT     = 587
  EMAIL_USERNAME = sizning@gmail.com
  EMAIL_PASSWORD = xxxx xxxx xxxx xxxx   ← App Password!
  EMAIL_FROM     = sizning@gmail.com
  EMAIL_USE_TLS  = True
─────────────────────────────────────────────────────────────────
"""

import asyncio
import logging
import random
import smtplib
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config.config import (
    EMAIL_FROM,
    EMAIL_HOST,
    EMAIL_PASSWORD,
    EMAIL_PORT,
    EMAIL_USE_TLS,
    EMAIL_USERNAME,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# OTP GENERATSIYA
# ──────────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """6 xonali raqamli OTP kod yaratadi."""
    return "".join(random.choices(string.digits, k=length))


# ──────────────────────────────────────────────────────────────────────
# EMAIL XABAR SHABLONI (HTML)
# ──────────────────────────────────────────────────────────────────────

def _build_email_html(otp_code: str, full_name: str, expire_minutes: int = 10) -> str:
    """Chiroyli HTML email shablonini qaytaradi."""
    return f"""
    <!DOCTYPE html>
    <html lang="uz">
    <head>
      <meta charset="UTF-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      <title>Tasdiqlash kodi</title>
    </head>
    <body style="margin:0;padding:0;background:#0f0f1a;font-family:'Segoe UI',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0"
             style="background:#0f0f1a;padding:40px 0;">
        <tr><td align="center">
          <table width="520" cellpadding="0" cellspacing="0"
                 style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
                        border-radius:16px;overflow:hidden;
                        box-shadow:0 20px 60px rgba(0,0,0,0.5);">

            <!-- HEADER -->
            <tr>
              <td style="background:linear-gradient(90deg,#667eea,#764ba2);
                          padding:32px;text-align:center;">
                <div style="font-size:36px;margin-bottom:8px;">🚚</div>
                <h1 style="color:#fff;margin:0;font-size:24px;
                            font-weight:700;letter-spacing:1px;">
                  Logistika AI
                </h1>
                <p style="color:rgba(255,255,255,0.8);margin:6px 0 0;
                           font-size:14px;">
                  Premium logistika platformasi
                </p>
              </td>
            </tr>

            <!-- BODY -->
            <tr>
              <td style="padding:40px 36px;">
                <p style="color:#a0aec0;font-size:15px;margin:0 0 16px;">
                  Salom, <strong style="color:#e2e8f0;">{full_name}</strong>!
                </p>
                <p style="color:#718096;font-size:14px;margin:0 0 28px;
                           line-height:1.7;">
                  Ro'yxatdan o'tishni tasdiqlash uchun quyidagi
                  <strong style="color:#a0aec0;">bir martalik kodni</strong> kiriting.
                  Kod <strong style="color:#f6ad55;">{expire_minutes} daqiqa</strong>
                  ichida amal qiladi.
                </p>

                <!-- OTP BOX -->
                <div style="text-align:center;margin:0 0 32px;">
                  <div style="display:inline-block;
                               background:linear-gradient(135deg,#667eea20,#764ba220);
                               border:2px solid #667eea;
                               border-radius:12px;
                               padding:20px 40px;">
                    <span style="font-size:42px;font-weight:900;
                                 letter-spacing:12px;color:#e2e8f0;
                                 font-family:'Courier New',monospace;">
                      {otp_code}
                    </span>
                  </div>
                </div>

                <p style="color:#4a5568;font-size:12px;
                           text-align:center;margin:0;">
                  ⚠️ Agar siz ro'yxatdan o'tmagan bo'lsangiz,
                  ushbu xatni e'tiborsiz qoldiring.
                </p>
              </td>
            </tr>

            <!-- FOOTER -->
            <tr>
              <td style="background:#0d0d1f;padding:20px 36px;text-align:center;
                          border-top:1px solid #1a1a2e;">
                <p style="color:#2d3748;font-size:12px;margin:0;">
                  © 2025 Logistika AI · Barcha huquqlar himoyalangan
                </p>
              </td>
            </tr>

          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """


# ──────────────────────────────────────────────────────────────────────
# EMAIL YUBORISH (SINXRON — thread-safe)
# ──────────────────────────────────────────────────────────────────────

def _send_email_sync(to_email: str, otp_code: str, full_name: str) -> None:
    """
    SMTP orqali email yuboradi (sinxron).
    Bu funksiya asyncio.to_thread() orqali chaqiriladi.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔐 Tasdiqlash kodi: {otp_code} — Logistika AI"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = to_email

    # Oddiy matn (fallback uchun)
    plain_text = (
        f"Salom, {full_name}!\n\n"
        f"Tasdiqlash kodingiz: {otp_code}\n\n"
        f"Kod 10 daqiqa ichida amal qiladi.\n\n"
        f"— Logistika AI"
    )
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(_build_email_html(otp_code, full_name), "html", "utf-8"))

    # SMTP ulanish
    try:
        if EMAIL_USE_TLS:
            # Port 587 → STARTTLS
            smtp = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10)
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
        else:
            # Port 465 → SSL
            smtp = smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, timeout=10)

        smtp.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_FROM, to_email, msg.as_string())
        smtp.quit()
        logger.info("✅ Email yuborildi: %s", to_email)
    except Exception as exc:
        logger.error("❌ Email yuborishda xato: %s", exc)
        raise


# ──────────────────────────────────────────────────────────────────────
# ASYNC WRAPPER
# ──────────────────────────────────────────────────────────────────────

async def send_otp_email(to_email: str, otp_code: str, full_name: str) -> None:
    """
    OTP kodini email ga asinxron yuboradi.

    Args:
        to_email:  Qabul qiluvchining email manzili
        otp_code:  6 xonali OTP kod
        full_name: Foydalanuvchining to'liq ismi (xatda ko'rsatiladi)

    Raises:
        Exception: SMTP ulanish yoki yuborish xatosi
    """
    await asyncio.to_thread(_send_email_sync, to_email, otp_code, full_name)
