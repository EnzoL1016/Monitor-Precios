FROM python:3.11-slim

# Evita archivos .pyc y permite ver logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Definimos la ruta de los navegadores como variable de entorno global
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# 1. Instalamos dependencias para mysqlclient Y las necesarias para Playwright [cite: 2]
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    python3-dev \
    curl \
    libnss3 \
    libatk-bridge2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/* 

# 2. Copiamos e instalamos requerimientos de Python [cite: 4]
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Instalamos Playwright y los binarios del navegador Chromium
# Usamos la variable de entorno para que se instalen en /ms-playwright
RUN pip install playwright && \
    playwright install --with-deps chromium

# 4. Copiamos el resto del código (Corregido el espacio extra) 
COPY . .

EXPOSE 8000