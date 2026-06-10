from pathlib import Path

from backend.common.utils.frontend_ui_audit import analyze_frontend_ui, evaluate_thresholds


def test_frontend_ui_audit_returns_metrics():
    project_root = Path(__file__).resolve().parents[3]
    result = analyze_frontend_ui(project_root)

    assert "summary" in result
    assert "css" in result
    assert "templates" in result
    assert result["summary"]["css_total"] > 0
    assert result["summary"]["templates_total"] > 0


def test_frontend_ui_threshold_evaluation_shape():
    project_root = Path(__file__).resolve().parents[3]
    result = analyze_frontend_ui(project_root)
    threshold = evaluate_thresholds(result)

    assert "checks" in threshold
    assert "failing_checks" in threshold
    assert "passed" in threshold
