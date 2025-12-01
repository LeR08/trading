# Dockerfile pour Kraken BTC Trading Bot avec marge x3
FROM python:3.11-slim

# Metadata
LABEL maintainer="trading-team"
LABEL description="Kraken BTC Trading Bot with 3x leverage"
LABEL version="1.0"

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Créer user non-root pour sécurité
RUN useradd -m -u 1000 -s /bin/bash trader && \
    mkdir -p /app /app/logs /app/data && \
    chown -R trader:trader /app

WORKDIR /app

# Copier requirements et installer dépendances
COPY --chown=trader:trader requirements_bot.txt .
RUN pip install --no-cache-dir -r requirements_bot.txt

# Copier le code source
COPY --chown=trader:trader src/ ./src/
COPY --chown=trader:trader example_run.py .
COPY --chown=trader:trader .env.example .env

# Exposer ports
# 9090: Prometheus metrics
EXPOSE 9090

# Passer à l'utilisateur non-root
USER trader

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:9090/health', timeout=5)" || exit 1

# Point d'entrée
# Note: En production, utiliser un process manager comme supervisord
# pour gérer le bot et le serveur de métriques
CMD ["python", "example_run.py"]
