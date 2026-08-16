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

# Run Uvicorn using the dynamic PORT environment variable provided by Render (fallback to 10000)
CMD ["sh", "-c", "uvicorn fleetflow_interactive_demo:app --host 0.0.0.0 --port ${PORT:-10000}"]
