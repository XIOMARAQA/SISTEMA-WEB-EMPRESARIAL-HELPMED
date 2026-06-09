# HelpMed

Sistema web de **logística médica** para **Seguricel S.A.C.**, con gestión de riesgos de seguridad de la información según **ISO/IEC 27005** e integración con controles alineados a **ISO/IEC 27001**.

## Descripción

HelpMed centraliza procesos operativos (recepción de insumos, control de calidad, inventario, control ambiental) y un módulo de **ciberseguridad** que permite:

- Inventario de activos, amenazas y vulnerabilidades
- Evaluación de riesgos (probabilidad × impacto) y matriz de calor
- Tratamiento de riesgos y registro de controles ISO 27001
- Auditoría automática de acciones en el sistema
- Alertas de seguridad (login fallido, cuenta bloqueada)
- Reportes exportables (PDF / Excel)

## Stack tecnológico

| Capa        | Tecnología                          |
| ----------- | ----------------------------------- |
| Frontend    | Vue 3, Vite, Pinia, Vue Router, Bootstrap 5 |
| Backend     | Django 5.2, Django REST Framework   |
| Autenticación | JWT (Simple JWT)                |
| Base de datos | PostgreSQL (esquema `helpmed`)  |

## Estructura del proyecto

```
Helpmed/
├── backend/          # API Django (manage.py)
├── frontend/         # SPA Vue 3 + Vite
├── requirements.txt  # Dependencias Python
└── README.md
```

## Requisitos previos

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Git

## Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd Helpmed
```

### 2. Backend

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
cd backend
copy .env.example .env          # Windows
# cp .env.example .env          # Linux / macOS
```

Editar `backend/.env` con credenciales reales de PostgreSQL, `SECRET_KEY` y demás variables.

Crear el esquema en PostgreSQL (si no existe):

```sql
CREATE SCHEMA IF NOT EXISTS helpmed;
```

Migrar y cargar datos iniciales:

```bash
python manage.py migrate
python manage.py seed_roles
python manage.py seed_usuarios_actores
python manage.py seed_maestros
python manage.py createsuperuser
```

Iniciar el servidor:

```bash
python manage.py runserver
```

API disponible en: `http://127.0.0.1:8000/api/`

### 3. Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Aplicación en: `http://localhost:5173`

## Variables de entorno

Los archivos `.env` y `.env.example` **no se versionan** (están en `.gitignore`).

| Archivo | Uso |
| ------- | --- |
| `backend/.env.example` | Plantilla local — copiar a `backend/.env` |
| `frontend/.env.example` | Plantilla local — copiar a `frontend/.env` |

Variables clave del backend: `SECRET_KEY`, `DB_*`, `CORS_ALLOWED_ORIGINS`, `MAX_LOGIN_ATTEMPTS`.

Variables clave del frontend: `VITE_API_PROXY_TARGET`, `VITE_API_BASE_URL`.

## Módulos principales

| Módulo | Descripción |
| ------ | ----------- |
| Recepción | Facturas, órdenes de compra, validación documental |
| Calidad | Inspección y control de calidad de insumos |
| Inventario | Stock, kardex, cuadre físico, vencimientos |
| Ambiental | Mediciones de temperatura/humedad |
| Gestión ISO 27005 | Activos, amenazas, vulnerabilidades, riesgos, matriz |
| Auditoría | Registro automático de acciones y auditorías formales |
| Reportes | Exportación PDF/Excel (matriz de riesgos, inventario, etc.) |
| Usuarios | Gestión de usuarios y roles |

## Roles del sistema

- **admin** — Acceso total
- **auditor_seguridad** — Riesgos, auditoría, alertas de seguridad
- **jefe_compras**, **jefe_almacen**, **operario_almacen**, **encargado_calidad**
- **area_administrativa**, **jefe_operaciones**, **gerente_general**

Los permisos por módulo se definen en `backend/seguridad/modulos.py`.

## Seguridad implementada

- Login con usuario + correo + contraseña
- Bloqueo de cuenta tras intentos fallidos (`MAX_LOGIN_ATTEMPTS`)
- JWT con refresh token
- Control de acceso por roles (RBAC)
- Trazabilidad automática (POST/PUT/PATCH/DELETE en la API)
- Notificaciones a administrador y auditor ante accesos sospechosos

## Comandos útiles

```bash
# Backend (desde backend/)
python manage.py runserver
python manage.py migrate
python manage.py seed_roles
python manage.py test

# Frontend (desde frontend/)
npm run dev
npm run build
npm run preview
```

## Documentación API

Con el servidor en marcha:

- Swagger / OpenAPI: `http://127.0.0.1:8000/api/schema/swagger-ui/` (si está habilitado con drf-spectacular)

## Proyecto académico

**Título:** Identificación y análisis de riesgos según ISO/IEC 27005 para fortalecer la seguridad de la información en un sistema web de logística médica de Seguricel S.A.C., 2026.

## Licencia y uso

Proyecto desarrollado para Seguricel S.A.C. Uso interno / académico. No publicar credenciales ni archivos `.env` en el repositorio.
