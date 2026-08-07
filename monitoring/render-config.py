#!/usr/bin/env python3
"""Netdata konfiguratsiyalarini `.env` dagi qiymatlar bilan to'ldiradi.

NEGA KERAK: netdata o'zining konfiguratsiya fayllarida `${VAR}` ni kengaytirmaydi.
Ya'ni parollarni (DB_PASSWORD, RABBITMQ_PASSWORD, Telegram token) yo to'g'ridan-to'g'ri
faylga yozish — va git'ga qo'shib yuborish — kerak bo'lardi, yo qo'lda nusxa olib
tahrirlash. Shu skript uchinchi yo'lni beradi:

    monitoring/netdata/**        → git'da, `${VAR}` shablonlari bilan (sirlarsiz)
    monitoring/.rendered/netdata/**  → git'da EMAS, tayyor qiymatlar bilan
                                       (docker-compose aynan shuni mount qiladi)

Ishlatish:
    python3 monitoring/render-config.py          # `make mon-up` buni o'zi chaqiradi

Qo'llab-quvvatlanadigan sintaksis (bash'nikiga o'xshash, ichma-ich ham ishlaydi):
    ${VAR}                 — qiymat topilmasa xato bilan to'xtaydi
    ${VAR:-standart}       — qiymat topilmasa "standart"
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "monitoring" / "netdata"
DST = ROOT / "monitoring" / ".rendered" / "netdata"
ENV_FILE = ROOT / ".env"

# Faqat shu kengaytmalar kengaytiriladi; qolgani (README va h.k.) ko'chirilmaydi.
RENDER_SUFFIXES = {".conf"}

# `${NAME}` yoki `${NAME:-default}`. Standart qiymat ichida `}` bo'lmasligi shart —
# ichma-ich shablonlar tashqi tsikl orqali, ichkaridan tashqariga hal qilinadi.
PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^{}]*))?\}")


def load_env() -> dict[str, str]:
    """`.env` ni o'qiydi. Haqiqiy muhit o'zgaruvchilari ustunlik qiladi —
    shunda `MONITORING_TG_TOKEN=... make mon-up` ham ishlaydi."""
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # `KEY="qiymat"` yoki `KEY='qiymat'` — tirnoqlar olib tashlanadi
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[key] = value
    values.update(os.environ)
    return values


def expand(text: str, env: dict[str, str], where: Path) -> str:
    """`${VAR}` larni almashtiradi. Ichma-ich shablonlar uchun o'zgarish
    to'xtaguncha takrorlanadi."""
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name, default = match.group(1), match.group(2)
        value = env.get(name)
        if value is None or value == "":
            if default is not None:
                return default
            missing.append(name)
            return ""
        return value

    for _ in range(10):  # ichma-ich chuqurlik chegarasi — cheksiz tsikldan himoya
        expanded = PLACEHOLDER.sub(replace, text)
        if expanded == text:
            break
        text = expanded

    if missing:
        names = ", ".join(sorted(set(missing)))
        rel = where.relative_to(ROOT)
        sys.exit(
            f"XATO: {rel} da quyidagi o'zgaruvchilar .env da topilmadi: {names}\n"
            f"      .env.example dagi monitoring bo'limidan nusxa oling."
        )
    return text


def main() -> None:
    if not SRC.is_dir():
        sys.exit(f"XATO: {SRC} topilmadi")

    env = load_env()

    # Har safar toza boshlanadi — o'chirilgan shablon `.rendered/` da qolib ketmasin.
    if DST.exists():
        shutil.rmtree(DST)

    count = 0
    for path in sorted(SRC.rglob("*")):
        if path.is_dir():
            continue
        target = DST / path.relative_to(SRC)
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix in RENDER_SUFFIXES:
            target.write_text(
                expand(path.read_text(encoding="utf-8"), env, path), encoding="utf-8"
            )
        else:
            shutil.copy2(path, target)
        count += 1

    if not env.get("MONITORING_TG_TOKEN"):
        print(
            "Eslatma: MONITORING_TG_TOKEN bo'sh — Telegram alertlari yuborilmaydi.\n"
            "         Panel va grafiklar bundan qat'i nazar ishlaydi."
        )
    print(f"{count} ta konfiguratsiya fayli tayyorlandi → {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
