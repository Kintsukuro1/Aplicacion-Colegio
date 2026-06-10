# Runbook: Gateway + Backups

## 1. Levantar stack con gateway
```bash
docker compose up -d --build
docker compose -f docker-compose.yml -f docker-compose.gateway.yml up -d gateway
```

Gateway publicado en `http://localhost:8080`.

## 2. Verificar request-id
```bash
curl -i http://localhost:8080/api/v1/health/
```
Esperado: header `X-Request-ID` en respuesta.

## 3. Verificar rate limit
```bash
# Ejecutar rafagas a auth endpoint y observar 429
for i in {1..30}; do curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST http://localhost:8080/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"x","password":"x"}'; done
```

## 4. Backup diario PostgreSQL (Windows Task Scheduler)
Comando sugerido:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/backup_postgres.ps1 -BackupDir "C:/backups/colegio" -RetentionDays 30 -DbHost "localhost" -DbPort "5432" -DbName "colegio_db" -DbUser "colegio_user"
```

Variables requeridas antes de ejecutar:
- `PGPASSWORD`

## 5. Restore drill (manual)
```bash
pg_restore --clean --if-exists --host localhost --port 5432 --username colegio_user --dbname colegio_db C:/backups/colegio/colegio_db_YYYYMMDD_HHMMSS.dump
```

## 6. Invalidar cache por tenant
```bash
python manage.py invalidate_tenant_cache --tenant-id 12345 --namespace dashboard_summary
```
