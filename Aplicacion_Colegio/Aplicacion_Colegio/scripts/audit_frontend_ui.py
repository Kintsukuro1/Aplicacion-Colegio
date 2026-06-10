from __future__ import annotations

import argparse
from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.common.utils.frontend_ui_audit import (
    AuditThresholds,
    analyze_frontend_ui,
    build_text_report,
    evaluate_thresholds,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audita adopción del design system, responsive y accesibilidad básica del frontend."
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Ruta raíz del proyecto (por defecto: directorio actual).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Falla con exit code 1 si no se cumplen umbrales mínimos.",
    )
    parser.add_argument("--design-min", type=float, default=0.95)
    parser.add_argument("--responsive-min", type=float, default=0.60)
    parser.add_argument("--focus-min", type=float, default=0.60)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).resolve()

    audit_result = analyze_frontend_ui(project_root)
    threshold_result = evaluate_thresholds(
        audit_result,
        AuditThresholds(
            design_system_coverage_min=args.design_min,
            responsive_css_coverage_min=args.responsive_min,
            focus_style_coverage_min=args.focus_min,
        ),
    )

    print(build_text_report(audit_result, threshold_result))

    if args.strict and not threshold_result["passed"]:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
