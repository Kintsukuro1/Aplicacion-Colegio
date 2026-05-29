#!/usr/bin/env python
"""
Script helper para migrar datos de SQLite a PostgreSQL de forma segura en Django.
Uso: python scratch/migrate_db.py
"""
import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_FILE = BASE_DIR / "scratch" / "db_backup.json"
SQLITE_FILE = BASE_DIR / "db.sqlite3"


def run_command(command, env=None):
    """Ejecuta un comando en la consola de forma interactiva y retorna el código de salida."""
    print(f"\n> Ejecutando: {' '.join(command)}")
    try:
        res = subprocess.run(command, cwd=BASE_DIR, env=env, check=True)
        return res.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar el comando: {e}", file=sys.stderr)
        return False


def main():
    print("======================================================================")
    print("       SISTEMA DE MIGRACIÓN DE BASE DE DATOS: SQLITE -> POSTGRESQL     ")
    print("======================================================================")

    # 1. Comprobar la existencia del archivo de SQLite
    if not SQLITE_FILE.exists():
        print(f"⚠️  No se encontró el archivo de base de datos SQLite en: {SQLITE_FILE}")
        print("Se asumirá una migración o instalación limpia en PostgreSQL.")
        sqlite_exists = False
    else:
        print(f"✅ Se detectó base de datos SQLite activa en: {SQLITE_FILE}")
        sqlite_exists = True

    # Definir el entorno para la exportación (forzar SQLite temporalmente para exportar)
    export_env = os.environ.copy()
    export_env["DB_ENGINE"] = "sqlite"
    export_env["PYTHONUTF8"] = "1"

    # Definir el entorno para la importación (usar la config activa de .env / PostgreSQL)
    import_env = os.environ.copy()
    import_env["DB_ENGINE"] = "postgresql"
    import_env["PYTHONUTF8"] = "1"

    # 2. Exportar datos si SQLite existe
    if sqlite_exists:
        print("\n--- PASO 1: Exportando datos actuales de SQLite ---")
        print("Generando backup seguro (excluyendo tablas internas para evitar conflictos)...")
        
        # Excluimos contenttypes y permissions porque Django los crea automáticamente al hacer migrate
        # Excluimos sessions y admin log entries para evitar violaciones de integridad referencial históricas
        exclude_apps = [
            "contenttypes",
            "auth.Permission",
            "admin.logentry",
            "sessions"
        ]
        
        dump_cmd = [
            sys.executable, "manage.py", "dumpdata",
            "--indent", "2",
            "--output", str(BACKUP_FILE)
        ]
        for app in exclude_apps:
            dump_cmd.extend(["--exclude", app])

        if run_command(dump_cmd, env=export_env):
            print(f"✅ Datos exportados con éxito a: {BACKUP_FILE}")
        else:
            print("❌ Error al exportar los datos de SQLite. Abortando.")
            sys.exit(1)

    # 3. Aplicar migraciones en PostgreSQL
    print("\n--- PASO 2: Aplicando esquema de base de datos en PostgreSQL ---")
    print("Verifique que PostgreSQL esté corriendo y que las credenciales en su archivo .env sean válidas.")
    
    migrate_cmd = [sys.executable, "manage.py", "migrate"]
    
    if run_command(migrate_cmd, env=import_env):
        print("✅ Esquema de base de datos migrado correctamente en PostgreSQL.")
    else:
        print("❌ Error al aplicar las migraciones en PostgreSQL.")
        print("Asegúrese de haber creado la base de datos y de configurar correctamente su archivo .env")
        sys.exit(1)

    # 4. Cargar datos si SQLite existía y se exportaron correctamente
    if sqlite_exists and BACKUP_FILE.exists():
        print("\n--- PASO 3: Importando datos en PostgreSQL ---")
        print("Cargando el backup generado desde la base de datos anterior...")
        
        load_cmd = [sys.executable, "manage.py", "loaddata", str(BACKUP_FILE)]
        
        if run_command(load_cmd, env=import_env):
            print("✅ ¡DATOS MIGRADOS EXITOSAMENTE DE SQLITE A POSTGRESQL!")
            print("Ya puede levantar su servidor Django conectado a PostgreSQL.")
        else:
            print("❌ Error al cargar los datos en PostgreSQL mediante loaddata.")
            sys.exit(1)
    else:
        print("\n--- PASO 3: Instalación Limpia ---")
        print("✅ Base de datos inicializada de forma limpia en PostgreSQL.")
        print("Si desea crear un superusuario administrador, ejecute:")
        print("   python manage.py createsuperuser")

    print("\n======================================================================")
    print("                     PROCESO DE MIGRACIÓN COMPLETADO                   ")
    print("======================================================================")


if __name__ == "__main__":
    main()
