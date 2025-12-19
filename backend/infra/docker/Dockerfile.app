# Multi-stage build for production
FROM python:3.10-slim as builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/
COPY config/ ./config/

# Production stage
FROM python:3.10-slim

WORKDIR /app

# Copy from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /app /app

# Create non-root user
RUN useradd -m -u 1000 trading && \
    chown -R trading:trading /app && \
    mkdir -p /app/logs /app/data && \
    chown -R trading:trading /app/logs /app/data

USER trading

# Environment
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "trading.main"]
