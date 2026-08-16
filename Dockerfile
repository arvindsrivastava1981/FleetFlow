# Use an official lightweight Python image
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

# Expose Render default port
EXPOSE 10000

# Run the modular FastAPI factory using the dynamic PORT provided by Render.
# The new package entrypoint lives at backend.app.main:app. The legacy single-file
# prototype (fleetflow_interactive_demo:app) remains only as a dev tool until all
# routes are migrated into backend/app/api/ (see PROJECT_STRUCTURE.md §4).
# Note: WORKDIR is /app, and `COPY . .` above already placed /app/backend, so the
# package import `backend.app.main` resolves because --app-dir /app puts the repo
# root (which contains the `backend` package) onto sys.path.
CMD ["sh", "-c", "uvicorn backend.app.main:app --app-dir /app --host 0.0.0.0 --port ${PORT:-10000}"]
