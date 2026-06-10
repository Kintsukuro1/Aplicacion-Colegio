#!/usr/bin/env python
"""
Restaura PostgreSQL con scratch/db_backup.json (backup compartido del equipo).

Uso (desde Aplicacion_Colegio):
  python scratch/restore_team_backup.py

Detener runserver antes de ejecutar.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DB_ENGINE", "postgresql")
os.environ["PYTHONUTF8"] = "1"
os.environ["EMAIL_BACKEND"] = "django.core.mail.backends.dummy.EmailBackend"

BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_FILE = BASE_DIR / "scratch" / "db_backup.json"

sys.path.insert(0, str(BASE_DIR))
import django  # noqa: E402

django.setup()

from django.core import serializers  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import IntegrityError, transaction  # noqa: E402


def strip_bom():
    raw = BACKUP_FILE.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        BACKUP_FILE.write_bytes(raw[3:])
        print("[OK] BOM UTF-8 eliminado del backup")


def load_fixture_resilient():
    text = BACKUP_FILE.read_text(encoding="utf-8")
    stream = serializers.deserialize("json", text, ignorenonexistent=True)

    ok = skipped = errors = 0
    for obj in stream:
        try:
            obj.save()
            ok += 1
        except IntegrityError:
            skipped += 1
        except Exception as exc:
            errors += 1
            model = getattr(obj.object, "_meta", None)
            label = model.label if model else "?"
            print(f"  [WARN] {label} pk={getattr(obj.object, 'pk', '?')}: {exc}")

    print(f"[OK] Cargados: {ok} | duplicados omitidos: {skipped} | otros errores: {errors}")


def main():
    if not BACKUP_FILE.exists():
        print(f"No existe: {BACKUP_FILE}")
        sys.exit(1)

    print("=" * 70)
    print("  RESTAURAR BD = backup del equipo (scratch/db_backup.json)")
    print("  Borra datos actuales y recarga el JSON compartido en el repo.")
    print("=" * 70)

    strip_bom()

    print("\n> migrate")
    call_command("migrate", interactive=False, verbosity=1)

    print("\n> flush")
    call_command("flush", interactive=False, verbosity=0)

    print("\n> loaddata (modo tolerante a duplicados)...")
    load_fixture_resilient()

    print("\n> fix_pg_sequences")
    subprocess.run([sys.executable, str(BASE_DIR / "scratch" / "fix_pg_sequences.py")], check=True)

    print("\n" + "=" * 70)
    print("  Listo. Reinicia runserver.")
    print("  Profesor: javier.torres@colegio.cl")
    print("  Alumno:   alumno1@colegio.cl")
    print("=" * 70)


if __name__ == "__main__":
    main()
