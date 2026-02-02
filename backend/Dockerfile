# PartnerCalc OS - Backend Dockerfile
FROM python:3.11-slim

# הגדרות
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# התקנת dependencies מערכתיות
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# תיקיית עבודה
WORKDIR /app

# התקנת Python packages
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# העתקת קוד
COPY . .

# פורט
EXPOSE 8000

# הרצה
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
