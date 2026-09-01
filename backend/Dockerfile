# syntax=docker/dockerfile:1

# --- base: shared by dev and prod -----------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]

# --- dev: live-reload dev server -------------------------------------------
FROM base AS dev

COPY requirements/dev.txt requirements/dev.txt
COPY requirements/test.txt requirements/test.txt
RUN pip install --no-cache-dir -r requirements/dev.txt

# Source is bind-mounted by docker-compose for live reload; no COPY here.

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# --- prod: daphne (ASGI, required for Channels/websockets) ----------------
FROM base AS prod

COPY requirements/prod.txt requirements/prod.txt
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY . /app

RUN python manage.py collectstatic --noinput

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
