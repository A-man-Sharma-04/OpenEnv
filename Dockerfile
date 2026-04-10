FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONPATH=/app \
  PORT=7860

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create non-root user for security (HF Spaces compat)
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# HF Spaces / 8GB RAM compat: expose API port
EXPOSE 7860

# Serve API continuously so frontend and external clients can connect.
CMD ["python", "-m", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "7860"]

