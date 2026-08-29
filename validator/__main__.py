"""CLI: python -m validator <project.json> [--json]"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    as_json = False
    if "--json" in args:
        as_json = True
        args.remove("--json")
    if len(args) != 1 or args[0] in {"-h", "--help"}:
        sys.stderr.write("usage: python -m validator [--json] <project.json>\n")
        return 2
    path = Path(args[0])
    if not path.is_file():
        sys.stderr.write(f"file not found: {path}\n")
        return 2
    repo = Path(__file__).resolve().parent.parent
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from validator.validate import validate_path
    result = validate_path(path.resolve())
    if as_json:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        _print_human(result)
    return 0 if result["valid"] else 1


def _print_human(result: dict) -> None:
    if result["valid"]:
        extra = f"  warnings={len(result.get('warnings', []))}" if result.get("warnings") else ""
        sys.stdout.write(f"PASS{extra}\n")
        for w in result.get("warnings", []):
            sys.stdout.write(f"  WARN {w['layer']} {w['code']} {w['path']}: {w['message']}\n")
        return
    sys.stdout.write(f"FAIL  errors={len(result['errors'])}\n")
    for e in result["errors"]:
        sys.stdout.write(f"  {e['layer']} {e['code']} {e['path']}: {e['message']}\n")
    for w in result.get("warnings", []):
        sys.stdout.write(f"  WARN {w['layer']} {w['code']} {w['path']}: {w['message']}\n")


if __name__ == "__main__":
    raise SystemExit(main())
