FROM python:3.12-slim

# ---------- Basis ----------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ---------- Dependencies ----------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- App ----------
COPY app ./app

# ---------- Security ----------
RUN useradd -m appuser
USER appuser

# ---------- Start ----------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
