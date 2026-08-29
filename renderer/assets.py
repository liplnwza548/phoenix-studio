"""Resolve Phase 0 asset URIs to local files. No download. No generation."""

from pathlib import Path

from renderer.errors import RenderError

REPO_ROOT = Path(__file__).resolve().parent.parent
SUPPORTED_IMAGE_KIND = "image"


def resolve_uri(uri: str, project_path: Path) -> Path:
    if not isinstance(uri, str) or not uri:
        raise RenderError("Asset uri is empty.")
    if uri.startswith("asset://"):
        rel = uri[len("asset://") :]
        path = (REPO_ROOT / rel).resolve()
    else:
        raw = Path(uri)
        path = raw.resolve() if raw.is_absolute() else (project_path.parent / raw).resolve()
    return path


def require_image_file(asset: dict, project_path: Path) -> Path:
    kind = asset.get("kind")
    if kind != SUPPORTED_IMAGE_KIND:
        raise RenderError(f"Unsupported asset kind '{kind}'. Phase 2 renders still images only.")
    path = resolve_uri(asset.get("uri", ""), project_path)
    if not path.is_file():
        raise RenderError(f"Missing asset file: {path}")
    return path
