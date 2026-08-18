#── Stage 1: build the Vite/React SPA ─────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

# Copy dependency manifests first for layer caching, then the source.
COPY frontend/package*.json ./
# NOTE: do NOT add --omit=optional — rollup/esbuild ship their native binaries as
# optional dependencies; omitting them breaks the production build.
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
# Compile the static SPA. Vite outputs to frontend/dist (Tailwind pre-built via
# PostCSS — no CDN at runtime). Cache-busted by Vite's content-hashed assets.
RUN npm run build

#── Stage 2: Python runtime that serves the API + mounted SPA ──────────────────
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside the container
WORKDIR /app

# Install system dependencies (build-essential, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Copy the compiled SPA into the expected location. backend/app/main.py resolves
# `frontend/dist` relative to the repo root (/app), so this must land at
# /app/frontend/dist for the catch-all SPA fallback to activate.
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Expose Render default port
EXPOSE 10000

# Run the modular FastAPI factory using the dynamic PORT provided by Render.
# backend.app.main:app is the only entry point.
CMD ["sh", "-c", "uvicorn backend.app.main:app --app-dir /app --host 0.0.0.0 --port ${PORT:-10000}"]
