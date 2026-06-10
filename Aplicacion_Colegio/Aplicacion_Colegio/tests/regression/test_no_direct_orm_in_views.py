from __future__ import annotations

import re
from pathlib import Path


FORBIDDEN_PATTERNS = [
    re.compile(r"\.objects\."),
]

# Views pendientes de refactorizar a services
ALLOWED_ORM_VIEW_FILES = {
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


def test_views_have_no_direct_orm_access():
    project_root = Path(__file__).resolve().parents[2]

    violations: list[str] = []

    for file_path in _iter_view_files(project_root):
        relative_path = file_path.relative_to(project_root).as_posix()
        if relative_path in ALLOWED_ORM_VIEW_FILES:
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()

        for index, line in enumerate(lines, start=1):
            if line.strip().startswith("#"):
                continue

            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    relative_path = file_path.relative_to(project_root).as_posix()
                    violations.append(f"{relative_path}:{index}: {line.strip()}")

    assert not violations, (
        "Se detectó acceso ORM directo en views. "
        "Debe delegarse en services.\n" + "\n".join(violations)
    )
