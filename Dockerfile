FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN find /app/docker /app/scripts -maxdepth 1 -type f -name '*.sh' -exec chmod +x {} + \
    && chmod +x /app/deploy.sh /app/backup.sh /app/rollback.sh /app/restore.sh
RUN addgroup --system app && adduser --system --ingroup app app \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app

USER app

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["/app/docker/start-web.sh"]
