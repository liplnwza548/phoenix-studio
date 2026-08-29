"""Load Phase 0 schemas relative to the repository, not cwd."""

import json
from functools import lru_cache
from pathlib import Path

from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"
PROJECT_SCHEMA_ID = "https://phoenix.studio/schemas/project.schema.json"


@lru_cache(maxsize=1)
def registry() -> Registry:
    reg = Registry()
    for path in sorted(SCHEMAS_DIR.glob("*.json")):
        contents = json.loads(path.read_text(encoding="utf-8"))
        resource = Resource.from_contents(contents, default_specification=DRAFT202012)
        ident = contents.get("$id")
        if ident:
            reg = reg.with_resource(ident, resource)
        reg = reg.with_resource(path.name, resource)
    return reg


def project_schema() -> dict:
    return json.loads((SCHEMAS_DIR / "project.schema.json").read_text(encoding="utf-8"))
