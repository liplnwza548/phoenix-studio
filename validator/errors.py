"""Structured validation errors. Deterministic. No repair."""

from typing import Any, Dict, List, Optional

LAYERS = ("SCHEMA", "REFERENCE", "TIMELINE", "GEOMETRY", "TRUTH", "OUTPUT")
LAYER_RANK = {name: i for i, name in enumerate(LAYERS)}


class Issue:
    __slots__ = ("code", "path", "message", "severity", "layer")

    def __init__(self, code: str, path: str, message: str, severity: str, layer: str):
        self.code = code
        self.path = path
        self.message = message
        self.severity = severity
        self.layer = layer

    def as_dict(self) -> Dict[str, str]:
        return {
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "severity": self.severity,
            "layer": self.layer,
        }


def sort_issues(issues: List[Issue]) -> List[Issue]:
    return sorted(
        issues,
        key=lambda i: (LAYER_RANK.get(i.layer, 99), i.path, i.code, i.message),
    )


def result_payload(issues: List[Issue]) -> Dict[str, Any]:
    ordered = sort_issues(issues)
    errors = [i.as_dict() for i in ordered if i.severity == "error"]
    warnings = [i.as_dict() for i in ordered if i.severity == "warning"]
    out: Dict[str, Any] = {"valid": len(errors) == 0, "errors": errors}
    if warnings:
        out["warnings"] = warnings
    return out


def json_path(parts: List[Any]) -> str:
    if not parts:
        return "$"
    out = "$"
    for p in parts:
        if isinstance(p, int):
            out += f"[{p}]"
        else:
            out += f".{p}"
    return out
