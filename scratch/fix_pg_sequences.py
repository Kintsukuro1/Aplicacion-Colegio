#!/usr/bin/env python
"""Corrige secuencias de PostgreSQL tras loaddata (evita IntegrityError en login/axes)."""
import os
import sys
from io import StringIO
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DB_ENGINE", "postgresql")

import django

django.setup()

from django.apps import apps
from django.core.management import call_command
from django.db import connection

AXES_TABLES = ("axes_accesslog", "axes_accessattempt", "axes_accessfailurelog")


def _reset_table_sequence(table: str, column: str = "id") -> None:
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT COALESCE(MAX("{column}"), 0) FROM "{table}"')
        max_id = cursor.fetchone()[0] or 0
        cursor.execute(
            "SELECT setval(pg_get_serial_sequence(%s, %s), %s, true)",
            [table, column, max(max_id, 1)],
        )
    print(f"  {table}: secuencia -> {max(max_id, 1)}")


def main():
    labels = sorted(app.label for app in apps.get_app_configs())
    out = StringIO()
    call_command("sqlsequencereset", *labels, stdout=out)
    sql = out.getvalue().strip()

    executed = 0
    with connection.cursor() as cursor:
        for stmt in sql.split(";"):
            part = stmt.strip()
            if part and part.upper() not in ("BEGIN", "COMMIT"):
                cursor.execute(part)
                executed += 1

    print(f"sqlsequencereset: {executed} sentencias")

    print("Ajuste explicito django-axes:")
    for table in AXES_TABLES:
        _reset_table_sequence(table)

    print("[OK] Prueba iniciar sesion de nuevo.")


if __name__ == "__main__":
    main()
