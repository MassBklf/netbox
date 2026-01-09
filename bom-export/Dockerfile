# Basis-Image
FROM python:3.12-slim

# Umgebungsvariablen
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Arbeitsverzeichnis
WORKDIR /app

# System-Abhängigkeiten (für pandas/openpyxl)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python-Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code kopieren
COPY app.py .
COPY templates ./templates
COPY exports ./exports

# Port
EXPOSE 5000

# Startkommando
CMD ["python", "app.py"]