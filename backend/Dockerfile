#── Single stage: Python runtime serving ONLY the JSON API ────────────────────
# The React SPA (frontend/dist) is NOT built or copied here. It is deployed as a
# separate Render Static Site ("vahankhata-app", see render.yaml), so this image
# must never contain frontend/dist — otherwise backend/app/main.py would enable
# its conditional SPA fallback and serve index.html for unknown paths (e.g. a
# stray GET /sss would return the SPA shell instead of a 404). Keeping the API
# image SPA-free also makes builds faster and the image smaller.
#
# Build context is the backend/ folder (set via dockerContext in render.yaml),
# so all COPY paths below are relative to backend/.
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

# Copy application source code (backend/ contents → /app/).
# Since dockerContext is backend/, this copies backend/app/ to /app/app/,
# backend/__init__.py to /app/__init__.py, etc.
COPY . .

# Expose Render default port
EXPOSE 10000

# Run the modular FastAPI factory using the dynamic PORT provided by Render.
# Since the build context is backend/, the app module is at app.main:app
# (not backend.app.main:app as it was with root context).
CMD ["sh", "-c", "uvicorn app.main:app --app-dir /app --host 0.0.0.0 --port ${PORT:-10000}"]
