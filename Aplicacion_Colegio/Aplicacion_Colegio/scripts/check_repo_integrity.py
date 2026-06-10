#!/usr/bin/env python3
"""Repository integrity checks for CI/local quality gates.

Checks:
1) No unresolved merge conflict markers in repository files.
2) Root pytest configuration must point test discovery to root tests only.
"""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    '.git',
    '.venv',
    '.pytest_cache',
    '__pycache__',
    'node_modules',
    'media',
    'logs',
    # Mirror folder is not an execution source of truth for root CI.
    'Aplicacion_Colegio',
}
TEXT_EXTENSIONS = {
    '.py',
    '.md',
    '.txt',
    '.yml',
    '.yaml',
    '.json',
    '.html',
    '.css',
    '.js',
    '.ini',
    '.toml',
    '.env',
    '.sh',
    '.ps1',
}
CONFLICT_MARKERS = ('<<<<<<< ', '=======', '>>>>>>> ')


def _should_scan(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.name == '.env':
        return True
    return path.suffix.lower() in TEXT_EXTENSIONS


def _find_conflict_markers() -> list[str]:
    findings: list[str] = []
    for path in REPO_ROOT.rglob('*'):
        if not path.is_file() or not _should_scan(path):
            continue
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        for idx, line in enumerate(content.splitlines(), start=1):
            if any(marker in line for marker in CONFLICT_MARKERS):
                rel = path.relative_to(REPO_ROOT).as_posix()
                findings.append(f'{rel}:{idx}: merge marker found')
    return findings


def _check_pytest_source_of_truth() -> list[str]:
    findings: list[str] = []
    pytest_ini = REPO_ROOT / 'pytest.ini'
    if not pytest_ini.exists():
        findings.append('pytest.ini: missing (cannot enforce root test discovery)')
        return findings

    content = pytest_ini.read_text(encoding='utf-8', errors='ignore')
    normalized = '\n'.join(line.strip() for line in content.splitlines())
    if 'testpaths = tests' not in normalized:
        findings.append("pytest.ini: expected 'testpaths = tests' to enforce root-only discovery")
    return findings


def main() -> int:
    errors: list[str] = []
    errors.extend(_find_conflict_markers())
    errors.extend(_check_pytest_source_of_truth())

    if errors:
        print('Repository integrity check failed:')
        for item in errors:
            print(f' - {item}')
        return 1

    print('Repository integrity check passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
