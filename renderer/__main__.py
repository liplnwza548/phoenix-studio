"""CLI: python -m renderer <project.json> -o <output.mp4>"""

from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "-h" in args or "--help" in args or not args:
        sys.stderr.write("usage: python -m renderer <project.json> -o <output.mp4>\n")
        return 2
    out = None
    if "-o" in args:
        i = args.index("-o")
        if i + 1 >= len(args):
            sys.stderr.write("missing value for -o\n")
            return 2
        out = args[i + 1]
        del args[i : i + 2]
    if len(args) != 1 or out is None:
        sys.stderr.write("usage: python -m renderer <project.json> -o <output.mp4>\n")
        return 2
    repo = Path(__file__).resolve().parent.parent
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from renderer.errors import RenderError
    from renderer.render import render

    try:
        path = render(args[0], out)
    except RenderError as exc:
        sys.stderr.write(f"ERROR {exc}\n")
        return 1
    sys.stdout.write(f"{path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
