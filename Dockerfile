FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies first (cache-friendly)
COPY pyproject.toml ./
COPY requirements.txt ./

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir \
    pytest>=8.0.0 \
    ruff>=0.5.0 \
    pyright>=1.1.389 \
    vulture>=2.10 \
    safety>=3.2.0 \
    python-dotenv>=1.0.0 \
    aiohttp>=3.9.0 \
    websockets>=12.0 \
    && pip cache purge

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Default environment variables (can be overridden)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENABLE_LLM=0
ENV LOG_LEVEL=INFO

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

# Default command - run once cycle or can be overridden
CMD ["python3", "cli.py", "--mode", "once"]