# Dockerfile for CDC Customs & Quota Manager (Streamlit)
FROM python:3.11-slim

# Prevent Python from writing .pyc and buffer output for realtime logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Install system dependencies (curl for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and assets
COPY app.py .
COPY app_pages/ ./app_pages/
COPY services/ ./services/
COPY .streamlit/ ./.streamlit/
COPY examples/ ./examples/
COPY reference/ ./reference/
COPY data/ ./data/

# Expose Streamlit default web port
EXPOSE 8501

# Healthcheck to ensure Streamlit server is active and responding
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start Streamlit application
CMD ["streamlit", "run", "app.py"]

