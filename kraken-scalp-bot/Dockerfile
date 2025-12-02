FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY example_run.py .

# Create directory for .env file (to be mounted)
RUN mkdir -p /app/.env.d

# Expose metrics port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run bot
CMD ["python", "-m", "src.bot"]
