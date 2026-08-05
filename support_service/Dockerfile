# Support mikroservizining o'z image'i.
#
# Build konteksti — loyiha ildizi (docker-compose'da `context: .`), lekin ichiga
# faqat `support_service/` papkasi ko'chiriladi: mikroserviz asosiy kodga
# bog'liq emasligi image darajasida ham ta'minlanadi. Agar kimdir bexosdan
# `from order.models import ...` yozsa, konteynerda ImportError bilan darhol
# ko'rinadi — bu chegarani saqlaydigan eng arzon tekshiruv.

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY support_service/requirements.txt ./support_service/requirements.txt
RUN pip install --no-cache-dir -r support_service/requirements.txt

COPY support_service/ ./support_service/

EXPOSE 8000

CMD ["uvicorn", "support_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
