FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

# `docker build --target test -t modelia-runner-test runner && docker run --rm modelia-runner-test`
FROM base AS test
RUN pip install --no-cache-dir "pytest>=8.3,<9.0"
COPY tests ./tests
CMD ["python", "-m", "pytest", "-q", "tests"]

FROM base AS prod
# Runs as root (stage 1 mounts the raw socket in dev). In prod (docker-compose.prod.yml) it uses
# a restricted docker-socket-proxy through DOCKER_HOST instead (DD169).
EXPOSE 8090
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8090/healthz', timeout=2).status == 200 else 1)"
# Refuses to start (ConfigError) when RUNNER_TOKEN is empty.
CMD ["uvicorn", "app.main:build_default_app", "--factory", "--host", "0.0.0.0", "--port", "8090"]
