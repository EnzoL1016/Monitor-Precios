# 🔍 Price Tracker — Monitor de Precios E-commerce

Aplicación full-stack para el monitoreo automático de precios en sitios de e-commerce. Los usuarios registran productos desde sitios soportados o cualquier URL genérica, y el sistema realiza scraping automático cada hora para registrar el historial de precios y detectar variaciones.

🌐 **Demo en vivo:** [monitor-precios-one.vercel.app](https://monitor-precios-one.vercel.app)
🔌 **API:** [price-tracker-api.onrender.com](https://price-tracker-api.onrender.com)

---

## ✨ Features

- **Monitoreo automático cada hora** — Celery Beat dispara el scraping en background sin intervención del usuario
- **Multi-sitio** — Soporte para sitios populares con selectores optimizados y modo genérico para cualquier URL
- **Scraping con navegador real** — Playwright maneja sitios con JavaScript dinámico que BeautifulSoup no puede procesar
- **Historial de precios** — Registro completo de variaciones de precio a lo largo del tiempo por producto
- **Multi-usuario** — Cada usuario autenticado gestiona y visualiza únicamente sus propios productos
- **Autenticación JWT** — Registro, login y protección de endpoints con access/refresh tokens
- **Soft delete** — Los productos eliminados se marcan como inactivos preservando su historial

---

## 🛠️ Tech Stack

| Área | Tecnología |
|------|-----------|
| **Backend** | Django 4.2, Django REST Framework |
| **Autenticación** | djangorestframework-simplejwt |
| **Task Queue** | Celery 5.3 + Redis |
| **Frontend** | React, TypeScript, Vite |
| **Styling** | Tailwind CSS |
| **Base de datos** | PostgreSQL (Supabase en producción) |
| **Scraping** | BeautifulSoup4, Requests, Playwright, lxml |
| **Archivos estáticos** | WhiteNoise |
| **Containerización** | Docker, Docker Compose (desarrollo local) |

---

## 📁 Estructura del Proyecto

```
price-tracker/
├── backend/
│   ├── core/
│   │   ├── settings.py        # Configuración Django
│   │   ├── urls.py            # Rutas raíz
│   │   ├── celery.py          # Configuración Celery + Beat scheduler
│   │   └── wsgi.py
│   ├── products/
│   │   ├── models.py          # Product, PriceHistory
│   │   ├── scraper.py         # Lógica de scraping (sitios soportados + genérico)
│   │   ├── tasks.py           # Tarea Celery: scraping periódico cada hora
│   │   ├── views.py           # API endpoints (CRUD + historial)
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── migrations/
│   ├── manage.py
│   ├── requirements.txt
│   ├── build.sh               # Script de build para Render (collectstatic + migrate)
│   └── runtime.txt            # Versión de Python para Render
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Login.tsx
│   │   │   ├── ProductCard.tsx
│   │   │   └── ProductForm.tsx
│   │   ├── services/
│   │   │   └── api.ts         # Axios config + interceptors JWT
│   │   ├── types.ts
│   │   └── App.tsx
│   ├── vercel.json            # Rewrites para React Router en Vercel
│   ├── vite.config.ts
│   └── package.json
└── docker-compose.yml         # Entorno de desarrollo local
```

---

## ⚙️ Setup Local con Docker

### Prerrequisitos

- Docker y Docker Compose
- Git

### 1. Clonar el repositorio

```bash
git clone https://github.com/EnzoL1016/price-tracker.git
cd price-tracker
```

### 2. Configurar variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
# Django
SECRET_KEY=django-insecure-local-dev-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de datos
DB_NAME=pricetracker
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432

# Redis / Celery
REDIS_URL=redis://redis:6379/0

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

### 3. Levantar los servicios

```bash
docker-compose up --build
```

Esto levanta simultáneamente:

| Servicio | URL |
|----------|-----|
| Backend (Django) | `http://localhost:8000` |
| Frontend (React) | `http://localhost:5173` |
| PostgreSQL | puerto `5432` |
| Redis | puerto `6379` |
| Celery Worker | — |
| Celery Beat | — |

### 4. Migraciones y superusuario

```bash
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
```

### 5. Instalar Playwright (solo primera vez)

```bash
docker-compose exec backend playwright install chromium
```

---

## 🔌 API Endpoints

Todos los endpoints autenticados requieren el header:
```
Authorization: Bearer <access_token>
```

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/auth/register/` | Registro de usuario | ❌ |
| `POST` | `/api/auth/login/` | Login, retorna access + refresh token | ❌ |
| `POST` | `/api/auth/refresh/` | Renueva el access token | ❌ |
| `GET` | `/api/products/` | Lista los productos del usuario autenticado | ✅ |
| `POST` | `/api/products/` | Agrega un nuevo producto a monitorear | ✅ |
| `GET` | `/api/products/{id}/` | Detalle de un producto | ✅ |
| `DELETE` | `/api/products/{id}/` | Soft delete del producto | ✅ |
| `GET` | `/api/products/{id}/history/` | Historial completo de precios | ✅ |

---

## 🤖 Cómo funciona el scraping

El módulo `scraper.py` opera en dos modos:

**Sitios soportados:** Selectores CSS específicos y optimizados para la estructura HTML de cada sitio (MercadoLibre y otros). Más rápido y confiable.

**URL genérica:** Heurística de detección de precio sobre el DOM parseado: busca patrones numéricos con formato monetario en elementos `<span>`, `<p>` y `<meta>`. Para sitios con JavaScript dinámico, Playwright renderiza la página completa antes del análisis.

La tarea Celery se ejecuta **cada hora** vía `celery-beat`, itera todos los productos activos de todos los usuarios, y registra un nuevo `PriceHistory` solo si el precio cambió respecto al último registro.

---

## 📊 Modelos

```
Product
├── user            FK → User
├── name            CharField
├── url             URLField
├── current_price   DecimalField
├── created_at      DateTimeField
└── deleted_at      DateTimeField (null = activo)

PriceHistory
├── product         FK → Product
├── price           DecimalField
└── recorded_at     DateTimeField
```

---

## 🚀 Infraestructura de Producción

| Servicio | Plataforma | Detalle |
|----------|-----------|---------|
| Frontend | Vercel | Deploy automático desde `main` |
| API Django | Render (Web Service) | Build via `build.sh` |
| Celery Worker | Render (Background Worker) | `concurrency=1` en free tier |
| Celery Beat | Render (Background Worker) | Scheduler cada hora |
| PostgreSQL | Supabase | Session Pooler (IPv4, puerto 5432) |
| Redis | Upstash | Free tier, 10k comandos/día |

### Proyecto actualmente en producción:
https://monitor-precios-one.vercel.app/
