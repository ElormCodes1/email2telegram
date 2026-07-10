FROM python:3.13-slim

# Unbuffered stdout for real-time logs; no .pyc files in the image.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code (see .dockerignore for what's excluded).
COPY . .

# Run as a non-root user.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Default: run the read-only query API.
# To run the IMAP -> Telegram monitor instead, override the command:
#   docker run --env-file .env <image> python email2telegram.py
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
