"""
Script de auditoría de integridad de datos.

Detecta:
- Cursos sin ciclo académico
- Clases activas sin profesor
- Matrículas inválidas
- Relaciones rotas

Uso:
    python backend/scripts/audit_data_integrity.py
    python backend/scripts/audit_data_integrity.py --school-id 12345
    python backend/scripts/audit_data_integrity.py --json
"""

import argparse
import json
import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.apps.core.settings")

import django


django.setup()

from backend.apps.core.services.integrity_service import IntegrityService


def main():
    parser = argparse.ArgumentParser(description="Audita integridad del dominio escolar")
    parser.add_argument("--school-id", type=int, help="RBD del colegio a auditar")
    parser.add_argument("--json", action="store_true", help="Salida en formato JSON")

    args = parser.parse_args()

    if args.school_id:
        result = IntegrityService.get_school_integrity_report(args.school_id)
    else:
        result = IntegrityService.get_system_integrity_report()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human_readable(result, args.school_id)

    has_errors = _has_integrity_errors(result, args.school_id)
    sys.exit(1 if has_errors else 0)


def _has_integrity_errors(result, is_single_school):
    if is_single_school:
        return not result.get("is_valid", True)
    return result.get("invalid_schools", 0) > 0


def _print_human_readable(result, school_id):
    if school_id:
        print("=" * 80)
        print(f"AUDITORÍA DE INTEGRIDAD - COLEGIO {result['school_id']}")
        print("=" * 80)
        print(f"Estado: {'✅ VÁLIDO' if result['is_valid'] else '❌ INVÁLIDO'}")

        if result["errors"]:
            print("\nErrores detectados:")
            for error in result["errors"]:
                print(f"  - {error}")
        else:
            print("\nSin errores detectados.")

        print("\nDetalle:")
        for key, value in result["details"].items():
            print(f"  - {key}: {value}")
        return

    print("=" * 80)
    print("AUDITORÍA DE INTEGRIDAD - SISTEMA COMPLETO")
    print("=" * 80)
    print(f"Colegios analizados: {result['total_schools_analyzed']}")
    print(f"Colegios válidos: {result['valid_schools']}")
    print(f"Colegios con errores: {result['invalid_schools']}")

    schools_with_errors = [school for school in result["schools"] if not school["is_valid"]]
    if not schools_with_errors:
        print("\n✅ No se detectaron problemas de integridad.")
        return

    print("\n❌ Colegios con errores:")
    for school in schools_with_errors:
        print(f"\n  Colegio {school['school_id']}")
        for error in school["errors"]:
            print(f"    - {error}")


if __name__ == "__main__":
    main()
