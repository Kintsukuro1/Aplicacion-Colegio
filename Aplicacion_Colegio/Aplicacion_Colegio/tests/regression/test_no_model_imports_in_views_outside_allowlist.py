from __future__ import annotations

import re
from pathlib import Path


MODEL_IMPORT_PATTERN = re.compile(
    r"^\s*(from\s+(?:backend\.apps\.[\w\.]+\.models|\.\.models|\.models)\s+import|import\s+backend\.apps\.[\w\.]+\.models)"
)


ALLOWED_MODEL_IMPORT_VIEW_FILES = {
    "backend/apps/academico/views/academic_management_views.py",
    "backend/apps/accounts/views/profile.py",
    "backend/apps/accounts/views/student.py",
    "backend/apps/comunicados/views/comunicados.py",
    "backend/apps/core/views/admin_escolar/gestionar_apoderados.py",
    "backend/apps/core/views/admin_escolar/gestionar_ciclos.py",
    "backend/apps/core/views/admin_escolar/gestionar_cursos.py",
    "backend/apps/core/views/admin_escolar/gestionar_estudiantes.py",
    "backend/apps/core/views/admin_escolar/setup_wizard.py",
    "backend/apps/core/views/asesor_financiero/becas_api.py",
    "backend/apps/core/views/asesor_financiero/boletas_api.py",
    "backend/apps/core/views/asesor_financiero/cuotas_api.py",
    "backend/apps/core/views/asesor_financiero/dashboard_api.py",
    "backend/apps/core/views/asesor_financiero/estados_cuenta_api.py",
    "backend/apps/core/views/asesor_financiero/pagos_api.py",
    "backend/apps/core/views/estudiante/certificados.py",
    "backend/apps/core/views/estudiante/tareas.py",
    "backend/apps/core/views/profesor/asistencia.py",
    "backend/apps/core/views/profesor/gestionar_tareas.py",
    "backend/apps/core/views/profesor/mis_clases.py",
    # Pendientes de refactorizar a services:
    "backend/apps/core/views/estudiante/api.py",
    "backend/apps/core/views/soporte_tecnico/api.py",
    "backend/apps/core/views/inspector_convivencia/api.py",
    "backend/apps/core/views/apoderado/api.py",
    "backend/apps/core/views/coordinador_academico/api.py",
    "backend/apps/core/views/psicologo_orientador/api.py",
    "backend/apps/core/views/bibliotecario_digital/api.py",
}


def _iter_view_files(project_root: Path):
    backend_root = project_root / "backend" / "apps"
    yield from backend_root.glob("**/views.py")
    yield from backend_root.glob("**/views/**/*.py")


def test_views_do_not_import_models_outside_allowlist():
    project_root = Path(__file__).resolve().parents[2]

    violations: list[str] = []

    for file_path in _iter_view_files(project_root):
        relative_path = file_path.relative_to(project_root).as_posix()
        if relative_path in ALLOWED_MODEL_IMPORT_VIEW_FILES:
            continue

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for index, line in enumerate(text.splitlines(), start=1):
            if MODEL_IMPORT_PATTERN.search(line):
                violations.append(f"{relative_path}:{index}: {line.strip()}")

    assert not violations, (
        "Se detectaron imports directos de modelos en views fuera de la allowlist. "
        "Mueve esas dependencias a services o agrega una excepción explícita justificada.\n"
        + "\n".join(violations)
    )
