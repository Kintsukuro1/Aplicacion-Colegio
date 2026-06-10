# Documentación de Instalación - Aplicación Colegio

## Requisitos del Sistema

### Python
- **Versión requerida**: Python 3.12 o superior
- **Verificar versión**: `python --version`

### Bases de Datos Soportadas

#### Desarrollo
- **SQLite** (incluido con Python) - Configuración por defecto

#### Producción
- **PostgreSQL 14+** (Recomendado)
- **SQL Server** (Alternativa para entornos Windows con Active Directory)

### Servicios Externos (Producción)
- **Redis 6+** (para Channel Layers / WebSocket)
- **SMTP Server** (para envío de emails - SendGrid, Gmail, AWS SES)

---

## Instalación Local (Desarrollo)

### 1. Clonar el Repositorio
```bash
git clone <url-del-repositorio>
cd Aplicacion_Colegio
```

### 2. Crear Entorno Virtual
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar Dependencias
```bash
# Dependencias de producción
pip install -r requirements.txt

# Dependencias de desarrollo (opcional)
pip install -r requirements-dev.txt
```

### 4. Configurar Variables de Entorno
```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env y configurar:
# - SECRET_KEY (generar una nueva)
# - DEBUG=True
# - DB_ENGINE=sqlite (para desarrollo)
# - PAYMENT_WEBHOOK_TOKEN o PAYMENT_WEBHOOK_SECRET (validación de webhooks)
```

### Notificaciones de Produccion

Definir en `.env` para habilitar canales productivos:

```env
# Email transaccional
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<usuario_smtp>
EMAIL_HOST_PASSWORD=<password_smtp>
DEFAULT_FROM_EMAIL=noreply@tu-dominio.cl
NOTIFICATIONS_EMAIL_ENABLED=True

# Push FCM (usar uno de los dos)
FCM_CREDENTIALS_FILE=/ruta/segura/firebase-service-account.json
# FCM_CREDENTIALS_JSON={...json completo...}
```

### Webhooks de Pagos

Si vas a recibir eventos desde un proveedor de pagos, define una de estas variables en `.env`:

```env
PAYMENT_WEBHOOK_TOKEN=token-compartido-opcional
PAYMENT_WEBHOOK_SECRET=secreto-hmac-opcional
```

Recomendación: usa `PAYMENT_WEBHOOK_SECRET` cuando el proveedor soporte firma HMAC y deja `PAYMENT_WEBHOOK_TOKEN` como respaldo temporal.

### 5. Generar SECRET_KEY
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 6. Aplicar Migraciones
```bash
python manage.py migrate
```

### 7. Crear Superusuario
```bash
python manage.py createsuperuser
```

### 8. Ejecutar Servidor de Desarrollo
```bash
python manage.py runserver
```

Acceder a: http://127.0.0.1:8000

---

## Configuración de Producción

### Deploy Reproducible con Docker

Se incluye configuración base para levantar app + PostgreSQL + Redis:

```bash
docker compose up --build
```

Servicios disponibles:
- App (Daphne/ASGI): `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

Notas:
- Revisa `docker-compose.yml` para credenciales por defecto de entorno local.
- Usa `.env` real para staging/producción.
- Ejecuta migraciones dentro del contenedor web cuando corresponda:

```bash
docker compose exec web python manage.py migrate
```

### CI/CD Base (GitHub Actions)

Se agregó workflow en `.github/workflows/ci.yml` con:
- PostgreSQL y Redis como servicios
- Instalación de dependencias
- `migrate` automático
- Ejecución de tests con coverage usando `.coveragerc`

### Base de Datos: PostgreSQL

#### 1. Instalar PostgreSQL
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS (Homebrew)
brew install postgresql

# Windows
# Descargar instalador desde https://www.postgresql.org/download/windows/
```

#### 2. Crear Base de Datos
```sql
-- Conectarse a PostgreSQL
sudo -u postgres psql

-- Crear usuario y base de datos
CREATE USER colegio_user WITH PASSWORD 'password_seguro';
CREATE DATABASE colegio_db OWNER colegio_user;
GRANT ALL PRIVILEGES ON DATABASE colegio_db TO colegio_user;
```

#### 3. Configurar .env
```bash
DB_ENGINE=postgresql
DB_NAME=colegio_db
DB_USER=colegio_user
DB_PASSWORD=password_seguro
DB_HOST=localhost
DB_PORT=5432
```

#### 4. Instalar Dependencias de PostgreSQL
```bash
pip install psycopg2-binary
```

#### 5. Migrar Datos de SQLite a PostgreSQL (Opcional)
```bash
# Exportar datos de SQLite
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 4 > backup.json

# Cambiar a PostgreSQL en .env
DB_ENGINE=postgresql

# Importar datos
python manage.py migrate
python manage.py loaddata backup.json
```

---

### Redis (Channel Layers)

#### 1. Instalar Redis
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS (Homebrew)
brew install redis

# Windows
# Usar WSL o descargar desde https://github.com/microsoftarchive/redis/releases
```

#### 2. Iniciar Redis
```bash
# Linux/Mac
redis-server

# Verificar
redis-cli ping
# Debe responder: PONG
```

#### 3. Configurar .env
```bash
REDIS_URL=redis://localhost:6379/0
```

#### 4. Instalar Dependencias
```bash
pip install channels-redis
```

---

### Email SMTP

#### Opción 1: SendGrid (Recomendado - 100 emails/día gratis)
1. Crear cuenta en https://sendgrid.com
2. Generar API Key
3. Configurar .env:
```bash
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=<tu-api-key>
```

#### Opción 2: Gmail (Desarrollo/Testing)
1. Habilitar autenticación de 2 factores
2. Generar App Password: https://myaccount.google.com/apppasswords
3. Configurar .env:
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=<app-password>
```

#### Opción 3: AWS SES (Producción a gran escala)
```bash
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<aws-access-key-id>
EMAIL_HOST_PASSWORD=<aws-secret-access-key>
```

---

## Verificación de Configuración

### Verificar Sistema
```bash
# Chequeo de configuración
python manage.py check

# Chequeo de deployment
python manage.py check --deploy
```

### Ejecutar Tests
```bash
# Todos los tests
pytest

# Tests específicos
pytest tests/functional/
pytest tests/unit/
```

### Verificar Email
```python
# Shell de Django
python manage.py shell

from django.core.mail import send_mail
send_mail(
    'Test',
    'Mensaje de prueba',
    'noreply@colegio.cl',
    ['test@example.com'],
)
```

---

## Problemas Comunes

### PostgreSQL: Error de conexión
```
Error: FATAL: la autenticación de la contraseña falló para el usuario "colegio_user"
```
**Solución**: Verificar contraseña en .env y permisos en PostgreSQL

### Redis: Connection refused
```
Error: Error 111 connecting to localhost:6379. Connection refused.
```
**Solución**: Iniciar Redis con `redis-server`

### Email: SMTPAuthenticationError
```
Error: (535, b'5.7.8 Username and Password not accepted')
```
**Solución Gmail**: Generar App Password, no usar contraseña normal

---

## Siguientes Pasos

1. ✅ Instalación completada
2. ✅ Base de datos configurada
3. ✅ Redis configurado (producción)
4. ✅ Email configurado (producción)
5. ⏳ Configurar deployment (Docker, ver DEPLOYMENT.md)
6. ⏳ Configurar backups (ver BACKUP.md)

---

**Última actualización**: 16 de febrero, 2026  
**Versión**: 1.0.0
