# Spotifree — one image: Vite SPA + FastAPI (Postgres + R2 via env).
# Single-platform hosts (Railway / Render): build this Dockerfile, attach Postgres, set env vars.
FROM node:22-bookworm AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ ./backend/
COPY --from=frontend /src/frontend/dist ./frontend/dist
ENV FRONTEND_DIST=/app/frontend/dist \
    PYTHONPATH=/app/backend \
    ENVIRONMENT=production
WORKDIR /app/backend
# Railway / Render inject PORT; local / Compose default to 8000.
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
