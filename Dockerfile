FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir uv \
    && adduser --disabled-password --gecos "" appuser

# Dependencies first (better layer caching). --no-dev leaves out coverage/debug-toolbar.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# collectstatic only needs the settings to import, not a real database or real secrets.
# These throw-away values exist for this single build step and are NOT stored in the image env.
RUN SECRET_KEY="build-only-placeholder" \
    DATABASE_URL="sqlite:///:memory:" \
    ALLOWED_HOSTS="localhost" \
    SECURE_SSL_REDIRECT="False" \
    python manage.py collectstatic --noinput \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Real SECRET_KEY / DATABASE_URL / ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS are passed at `docker run`.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
