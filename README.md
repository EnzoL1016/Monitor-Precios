# 🔍 Price Tracker — Monitor de Precios E-commerce

Aplicación full-stack para el monitoreo automático de precios en sitios de e-commerce. Los usuarios registran productos desde sitios soportados o cualquier URL genérica, y el sistema realiza scraping automático cada hora para registrar el historial de precios y detectar variaciones.

🌐 **Demo en vivo:** [monitor-precios-one.vercel.app](https://monitor-precios-one.vercel.app)
🔌 **API:** [monitor-precios.onrender.com](https://monitor-precios.onrender.com)

---

## ✨ Features

- **Monitoreo automático cada hora** — APScheduler dispara el scraping en background dentro del mismo proceso Django
- **Multi-sitio** — Soporte para sitios populares con selectores optimizados y modo genérico para cualquier URL
- **Historial de precios** — Registro completo de variaciones de precio a lo largo del tiempo por producto
- **Alertas por email** — Notificación automática cuando un producto alcanza el precio objetivo
- **Multi-usuario** — Cada usuario autenticado gestiona y visualiza únicamente sus propios productos
- **Autenticación JWT** — Registro, login y protección de endpoints con access/refresh tokens
- **Soft delete** — Los productos eliminados se marcan como inactivos preservando su historial

---

## 🛠️ Tech Stack

| Área | Tecnología |
|------|-----------|
| **Backend** | Django 4.2, Django REST Framework |
| **Autenticación** | djangorestframework-simplejwt |
| **Scheduler** | APScheduler + django-apscheduler |
| **Frontend** | React, TypeScript, Vite |
| **Styling** | Tailwind CSS |
| **Base de datos** | PostgreSQL (Supabase en producción) |
| **Scraping** | BeautifulSoup4, Requests, lxml |
| **Archivos estáticos** | WhiteNoise |
| **Containerización** | Docker, Docker Compose (desarrollo local) |

> **Nota sobre scraping:** La versión en producción usa `requests` + `BeautifulSoup` para compatibilidad con el free tier de Render. La versión local con Docker incluye soporte completo para **Playwright** (scraping con navegador real para sitios con JavaScript dinámico como CompraGamer y Amazon).

---

## 📁 Estructura del Proyecto

```
price-tracker/
├── backend/
│   ├── core/
│   │   ├── settings.py        # Configuración Django
│   │   ├── urls.py            # Rutas raíz
│   │   └── wsgi.py
│   ├── products/
│   │   ├── models.py          # Product, PriceHistory
│   │   ├── scraper.py         # Lógica de scraping
│   │   ├── tasks.py           # Función de scraping periódico
│   │   ├── apps.py            # Registro del scheduler al arrancar Django
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
└── docker-compose.yml         # Entorno de desarrollo local completo
```

---

## ⚙️ Setup Local con Docker (versión completa con Playwright)

La versión local incluye Playwright para scraping completo, Celery para procesamiento asíncrono distribuido y Redis como broker de mensajes.

### Prerrequisitos

- Docker y Docker Compose
- Git

### 1. Clonar el repositorio

```bash
git clone https://github.com/EnzoL1016/Monitor-Precios.git
cd Monitor-Precios
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

# Email (opcional para alertas locales)
EMAIL_HOST_USER=tu@gmail.com
EMAIL_HOST_PASSWORD=tu_app_password
```

### 3. Levantar los servicios

```bash
docker-compose up --build
```

Esto levanta simultáneamente:

| Servicio | URL / Puerto |
|----------|-------------|
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

Con Playwright instalado el scraper usa un navegador real para sitios con JavaScript dinámico (CompraGamer, Amazon, etc.), logrando cobertura completa de sitios.

---

## 🔌 API Endpoints

Todos los endpoints autenticados requieren el header:
```
Authorization: Bearer <access_token>
```

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/register/` | Registro de usuario | ❌ |
| `POST` | `/api/token/` | Login, retorna access + refresh token | ❌ |
| `POST` | `/api/token/refresh/` | Renueva el access token | ❌ |
| `GET` | `/api/items/` | Lista los productos del usuario autenticado | ✅ |
| `POST` | `/api/items/` | Agrega un nuevo producto a monitorear | ✅ |
| `GET` | `/api/items/{id}/` | Detalle de un producto | ✅ |
| `DELETE` | `/api/items/{id}/` | Soft delete del producto | ✅ |
| `GET` | `/api/items/trash/` | Lista productos eliminados | ✅ |
| `POST` | `/api/items/{id}/restore/` | Restaura un producto de la papelera | ✅ |
| `DELETE` | `/api/items/{id}/hard_delete/` | Eliminación permanente | ✅ |

---

## 🤖 Cómo funciona el scraping

El módulo `scraper.py` tiene dos estrategias según el entorno:

**Producción (requests + BeautifulSoup):** Obtiene el HTML directamente con `requests` y lo parsea con `BeautifulSoup`. Funciona para sitios cuyo precio está en el HTML inicial: MercadoLibre, Fravega, Maximus, y cualquier sitio con datos estructurados JSON-LD o meta tags de precio.

**Local con Docker (Playwright):** Para sitios que renderizan precios con JavaScript (CompraGamer, Amazon), Playwright lanza un navegador real que ejecuta el JS antes del parsing.

En ambos casos el scraper aplica la siguiente cadena de prioridades para encontrar el precio:
1. Selectores específicos por sitio (MercadoLibre, CompraGamer, Maximus)
2. Datos estructurados JSON-LD (`application/ld+json`)
3. Meta tags de precio (`og:price:amount`, `itemprop="price"`, etc.)
4. Heurística sobre selectores CSS genéricos de precio

APScheduler registra el job al arrancar Django vía `apps.py` y lo ejecuta **cada hora** dentro del mismo proceso. Itera todos los productos activos y registra un nuevo `PriceHistory` solo si el precio cambió. Si el precio alcanza el objetivo del usuario, dispara una **alerta por email**.

---

## 📊 Modelos

```
Product
├── user            FK → User
├── name            CharField
├── url             URLField
├── current_price   DecimalField
├── target_price    DecimalField
├── is_available    BooleanField
├── created_at      DateTimeField
└── deleted_at      DateTimeField (null = activo)

PriceHistory
├── product         FK → Product
├── captured_price  DecimalField
└── recorded_at     DateTimeField
```

---

## 🚀 Infraestructura de Producción

| Servicio | Plataforma | Detalle |
|----------|-----------|---------|
| Frontend | Vercel | Deploy automático desde `main` |
| API Django + Scheduler | Render (Web Service) | Build via `build.sh`, scheduler embebido |
| PostgreSQL | Supabase | Session Pooler (IPv4, puerto 5432) |

### Variables de entorno en producción (Render)

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Generada por Render |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `.onrender.com` |
| `DATABASE_URL` | Connection string de Supabase (Session Pooler) |
| `CORS_ALLOWED_ORIGINS` | URL de Vercel sin barra final |
| `EMAIL_HOST_USER` | Cuenta Gmail para alertas |
| `EMAIL_HOST_PASSWORD` | App password de Gmail |

### Variable de entorno en producción (Vercel)

| Variable | Valor |
|----------|-------|
| `VITE_API_BASE_URL` | `https://monitor-precios.onrender.com/api` |

