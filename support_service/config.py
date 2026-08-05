"""Support mikroservizining sozlamalari.

Bu xizmat ATAYLAB asosiy loyihaning `config/config.py` sidan foydalanmaydi: u
`BOT_TOKEN`, Yandex kaliti, OSRM manzili kabi o'ziga aloqasi yo'q o'nlab
o'zgaruvchini talab qiladi va asosiy bazaga ulanib qo'yadi. Mikroserviz faqat
o'ziga keragini biladi — shuning uchun bu yerda qisqa, mustaqil ro'yxat.

`SECRET_KEY` asosiy ilova bilan BIR XIL bo'lishi shart: token shu yerda tekshiriladi
(tarmoq bo'ylab qo'shimcha so'rovsiz). Bu — umumiy sir orqali ishonch, xizmatlar
o'rtasida to'g'ridan-to'g'ri HTTP bog'liqlik emas.
"""

from __future__ import annotations

import os


def _required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"{key} muhit o'zgaruvchisi belgilanishi shart")
    return value


SUPPORT_DB_URL = _required("SUPPORT_DB_URL")
SECRET_KEY = _required("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Ichki xodim rollari — murojaatlarning HAMMASINI ko'radi va holatini o'zgartiradi.
# Rol tokendagi `role` claim'idan olinadi (`users/auth.py: token_payload_for`).
STAFF_ROLES = frozenset({"admin", "manager"})
