"""
Frontend UI audit helpers.
Provides lightweight, dependency-free checks for design-system adoption,
responsive coverage and basic accessibility indicators.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


CSS_LINK_RE = re.compile(
    r"{%\s*static\s+['\"](?P<path>css/[^'\"]+\.css)['\"]\s*%}",
    flags=re.IGNORECASE,
)
EXTENDS_ANY_RE = re.compile(
    r"{%\s*extends\s+['\"](?P<parent>[^'\"]+)['\"]\s*%}",
    flags=re.IGNORECASE,
)
EXTENDS_BASE_RE = re.compile(
    r"{%\s*extends\s+['\"]base_app\.html['\"]\s*%}",
    flags=re.IGNORECASE,
)
VIEWPORT_RE = re.compile(r"name\s*=\s*['\"]viewport['\"]", flags=re.IGNORECASE)
INLINE_STYLE_RE = re.compile(r"\sstyle\s*=\s*['\"]", flags=re.IGNORECASE)
MEDIA_QUERY_RE = re.compile(r"@media\b", flags=re.IGNORECASE)
FOCUS_RE = re.compile(r":focus(?:-visible)?\b", flags=re.IGNORECASE)
REDUCED_MOTION_RE = re.compile(r"prefers-reduced-motion", flags=re.IGNORECASE)
CSS_VAR_RE = re.compile(r"var\(--", flags=re.IGNORECASE)
SMALL_FONT_RE = re.compile(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", flags=re.IGNORECASE)


@dataclass
class AuditThresholds:
    design_system_coverage_min: float = 0.95
    responsive_css_coverage_min: float = 0.60
    focus_style_coverage_min: float = 0.60


def _safe_pct(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _collect_files(base_path: Path, pattern: str) -> list[Path]:
    if not base_path.exists():
        return []
    return sorted([path for path in base_path.rglob(pattern) if path.is_file()])


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _resolve_parent_template(
    parent_reference: str,
    templates_root: Path,
    templates_by_rel: dict[str, Path],
    templates_by_name: dict[str, list[Path]],
) -> Path | None:
    normalized = parent_reference.replace("\\", "/")
    candidates = [
        normalized,
        normalized.removeprefix("frontend/templates/"),
    ]

    for candidate in candidates:
        if candidate in templates_by_rel:
            return templates_by_rel[candidate]

    parent_name = Path(normalized).name
    same_name_candidates = templates_by_name.get(parent_name, [])
    if len(same_name_candidates) == 1:
        return same_name_candidates[0]

    return None


def _collect_effective_template_data(
    template_path: Path,
    templates_root: Path,
    templates_by_rel: dict[str, Path],
    templates_by_name: dict[str, list[Path]],
    cache: dict[Path, dict],
    stack: set[Path],
) -> dict:
    if template_path in cache:
        return cache[template_path]

    if template_path in stack:
        return {
            "css_links": set(),
            "has_viewport": False,
            "covered_by_design_system": False,
            "extends_base": False,
            "parent": None,
        }

    stack.add(template_path)
    content = _read_text(template_path)

    own_css_links = {
        match.group("path").replace("\\", "/") for match in CSS_LINK_RE.finditer(content)
    }
    own_has_viewport = bool(VIEWPORT_RE.search(content))
    own_extends_base = bool(EXTENDS_BASE_RE.search(content))
    own_has_design_system_link = any(path.endswith("design-system.css") for path in own_css_links)

    parent_template = None
    parent_match = EXTENDS_ANY_RE.search(content)
    if parent_match:
        parent_template = _resolve_parent_template(
            parent_match.group("parent"),
            templates_root,
            templates_by_rel,
            templates_by_name,
        )

    parent_data = {
        "css_links": set(),
        "has_viewport": False,
        "covered_by_design_system": False,
        "extends_base": False,
    }
    if parent_template is not None:
        parent_data = _collect_effective_template_data(
            parent_template,
            templates_root,
            templates_by_rel,
            templates_by_name,
            cache,
            stack,
        )

    result = {
        "css_links": own_css_links | parent_data["css_links"],
        "has_viewport": own_has_viewport or parent_data["has_viewport"],
        "covered_by_design_system": (
            own_extends_base
            or own_has_design_system_link
            or parent_data["covered_by_design_system"]
        ),
        "extends_base": own_extends_base or parent_data["extends_base"],
        "parent": parent_template,
    }

    cache[template_path] = result
    stack.remove(template_path)
    return result


def analyze_frontend_ui(project_root: Path) -> dict:
    css_root = project_root / "frontend" / "static" / "css"
    templates_root = project_root / "frontend" / "templates"

    css_files = _collect_files(css_root, "*.css")
    html_templates = _collect_files(templates_root, "*.html")

    css_by_rel = {path.relative_to(css_root).as_posix(): path for path in css_files}
    templates_by_rel = {path.relative_to(templates_root).as_posix(): path for path in html_templates}
    templates_by_name: dict[str, list[Path]] = {}
    for path in html_templates:
        templates_by_name.setdefault(path.name, []).append(path)

    effective_cache: dict[Path, dict] = {}

    css_metrics = {
        "total": len(css_files),
        "with_design_tokens": 0,
        "with_media_query": 0,
        "with_focus_styles": 0,
        "with_reduced_motion": 0,
        "with_small_font_px": 0,
        "files_without_media_query": [],
        "files_without_focus_styles": [],
    }

    for css_path in css_files:
        content = _read_text(css_path)
        rel = css_path.relative_to(project_root).as_posix()

        if CSS_VAR_RE.search(content):
            css_metrics["with_design_tokens"] += 1

        if MEDIA_QUERY_RE.search(content):
            css_metrics["with_media_query"] += 1
        else:
            css_metrics["files_without_media_query"].append(rel)

        if FOCUS_RE.search(content):
            css_metrics["with_focus_styles"] += 1
        else:
            css_metrics["files_without_focus_styles"].append(rel)

        if REDUCED_MOTION_RE.search(content):
            css_metrics["with_reduced_motion"] += 1

        font_sizes = [float(match.group(1)) for match in SMALL_FONT_RE.finditer(content)]
        if any(size < 14 for size in font_sizes):
            css_metrics["with_small_font_px"] += 1

    templates_metrics = {
        "total": len(html_templates),
        "extending_base_app": 0,
        "with_viewport_meta": 0,
        "with_inline_styles": 0,
        "covered_by_design_system": 0,
        "linked_css_templates": 0,
        "responsive_risk_templates": [],
        "not_covered_by_design_system": [],
    }

    for template_path in html_templates:
        content = _read_text(template_path)
        rel = template_path.relative_to(project_root).as_posix()
        effective = _collect_effective_template_data(
            template_path,
            templates_root,
            templates_by_rel,
            templates_by_name,
            effective_cache,
            set(),
        )
        linked_css_rel = sorted(effective["css_links"])
        extends_base = bool(effective["extends_base"])
        has_design_system_link = bool(effective["covered_by_design_system"])

        if extends_base:
            templates_metrics["extending_base_app"] += 1

        if effective["has_viewport"]:
            templates_metrics["with_viewport_meta"] += 1

        if INLINE_STYLE_RE.search(content):
            templates_metrics["with_inline_styles"] += 1

        if linked_css_rel:
            templates_metrics["linked_css_templates"] += 1

        if extends_base or has_design_system_link:
            templates_metrics["covered_by_design_system"] += 1
        else:
            templates_metrics["not_covered_by_design_system"].append(rel)

        if linked_css_rel:
            css_targets = [css_by_rel.get(linked_css) for linked_css in linked_css_rel if linked_css in css_by_rel]
            has_responsive = any(path and MEDIA_QUERY_RE.search(_read_text(path)) for path in css_targets)
            if not has_responsive:
                templates_metrics["responsive_risk_templates"].append(rel)

    summary = {
        "css_total": css_metrics["total"],
        "templates_total": templates_metrics["total"],
        "design_system_coverage_pct": _safe_pct(
            templates_metrics["covered_by_design_system"], templates_metrics["total"]
        ),
        "responsive_css_coverage_pct": _safe_pct(
            css_metrics["with_media_query"], css_metrics["total"]
        ),
        "focus_style_coverage_pct": _safe_pct(
            css_metrics["with_focus_styles"], css_metrics["total"]
        ),
        "viewport_meta_coverage_pct": _safe_pct(
            templates_metrics["with_viewport_meta"], templates_metrics["total"]
        ),
        "templates_with_inline_styles_pct": _safe_pct(
            templates_metrics["with_inline_styles"], templates_metrics["total"]
        ),
    }

    return {
        "summary": summary,
        "css": css_metrics,
        "templates": templates_metrics,
    }


def evaluate_thresholds(audit_result: dict, thresholds: AuditThresholds | None = None) -> dict:
    thresholds = thresholds or AuditThresholds()
    summary = audit_result["summary"]

    checks = {
        "design_system_coverage": {
            "value": summary["design_system_coverage_pct"],
            "minimum": round(thresholds.design_system_coverage_min * 100, 2),
        },
        "responsive_css_coverage": {
            "value": summary["responsive_css_coverage_pct"],
            "minimum": round(thresholds.responsive_css_coverage_min * 100, 2),
        },
        "focus_style_coverage": {
            "value": summary["focus_style_coverage_pct"],
            "minimum": round(thresholds.focus_style_coverage_min * 100, 2),
        },
    }

    failing = [name for name, check in checks.items() if check["value"] < check["minimum"]]
    return {
        "checks": checks,
        "failing_checks": failing,
        "passed": len(failing) == 0,
    }


def build_text_report(audit_result: dict, threshold_result: dict | None = None) -> str:
    summary = audit_result["summary"]
    css_data = audit_result["css"]
    templates_data = audit_result["templates"]

    lines = [
        "Frontend UI Audit Report",
        "========================",
        f"CSS files: {summary['css_total']}",
        f"Templates: {summary['templates_total']}",
        "",
        "Coverage",
        "--------",
        f"Design system coverage: {summary['design_system_coverage_pct']}%",
        f"Responsive CSS coverage: {summary['responsive_css_coverage_pct']}%",
        f"Focus styles coverage: {summary['focus_style_coverage_pct']}%",
        f"Viewport meta coverage: {summary['viewport_meta_coverage_pct']}%",
        f"Templates with inline styles: {summary['templates_with_inline_styles_pct']}%",
        "",
        "Hotspots",
        "--------",
        f"CSS without media query: {len(css_data['files_without_media_query'])}",
        f"CSS without focus styles: {len(css_data['files_without_focus_styles'])}",
        f"Templates not covered by design system: {len(templates_data['not_covered_by_design_system'])}",
        f"Templates with responsive risk: {len(templates_data['responsive_risk_templates'])}",
    ]

    if threshold_result is not None:
        lines.extend([
            "",
            "Thresholds",
            "----------",
        ])
        for name, check in threshold_result["checks"].items():
            status = "OK" if check["value"] >= check["minimum"] else "FAIL"
            lines.append(
                f"{status} {name}: {check['value']}% (min {check['minimum']}%)"
            )

    return "\n".join(lines)
