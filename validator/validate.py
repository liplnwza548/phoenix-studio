"""Deterministic project validator. Does not mutate the plan."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from jsonschema import Draft202012Validator

from validator.errors import Issue, json_path, result_payload, sort_issues
from validator.schema_store import project_schema, registry

INSTANTANEOUS = frozenset({"cut", "cursor_click"})
TRANSFORMING = frozenset({"zoom_to_region", "pan_to_region", "fade"})
REQUIRES_TARGET = frozenset(
    {
        "zoom_to_region",
        "pan_to_region",
        "highlight_box",
        "spotlight_dim",
    }
)
FORBIDDEN_TRUTH = frozenset({"AI_GENERATED", "FICTIONAL"})
REC_DURATION = (15000, 30000)


def validate_path(path: Path | str) -> Dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        issue = Issue(
            code="JSON_PARSE",
            path="$",
            message=str(exc),
            severity="error",
            layer="SCHEMA",
        )
        return result_payload([issue])
    return validate_project(data)


def validate_project(project: Any) -> Dict[str, Any]:
    issues: List[Issue] = []
    issues.extend(_schema_issues(project))
    if not isinstance(project, dict):
        return result_payload(issues)
    # Semantic layers run even after schema errors when the object is a dict,
    # but they must not crash on missing structure.
    issues.extend(_reference_issues(project))
    issues.extend(_timeline_issues(project))
    issues.extend(_geometry_issues(project))
    issues.extend(_truth_issues(project))
    issues.extend(_output_issues(project))
    return result_payload(issues)


def _schema_issues(project: Any) -> List[Issue]:
    out: List[Issue] = []
    try:
        errors = list(Draft202012Validator(project_schema(), registry=registry()).iter_errors(project))
    except Exception as exc:
        return [
            Issue(
                code="SCHEMA_RESOLVE",
                path="$",
                message=str(exc),
                severity="error",
                layer="SCHEMA",
            )
        ]
    for err in errors:
        path = json_path(list(err.absolute_path))
        out.append(
            Issue(
                code="SCHEMA_ERROR",
                path=path,
                message=err.message,
                severity="error",
                layer="SCHEMA",
            )
        )
    return out
