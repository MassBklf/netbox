# Basis-Image
FROM python:3.12-slim

# Umgebungsvariablen
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Arbeitsverzeichnis
WORKDIR /app

# System-Abhängigkeiten
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Python-Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code kopieren
COPY app.py .
COPY templates ./templates
COPY static ./static

# Port
EXPOSE 5000

# Startkommando
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]