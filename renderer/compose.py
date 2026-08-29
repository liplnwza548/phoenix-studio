"""Compose project frames in memory. No FFmpeg. No AI."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from renderer.assets import require_image_file
from renderer.errors import RenderError

SUPPORTED = frozenset(
    {
        "hold",
        "crop_9_16",
        "highlight_box",
        "spotlight_dim",
        "kinetic_text",
        "cursor_move",
        "cursor_click",
        "zoom_to_region",
        "pan_to_region",
    }
)
DEFAULT_FONT = Path("/usr/share/fonts/SlidesCarnival/google/Sarabun/Sarabun-Regular.ttf")
HIGHLIGHT_STROKE = 4
HIGHLIGHT_COLOR = (255, 214, 0, 230)
SPOT_DEFAULT = 0.55
TEXT_FADE_MS = 200


def ms_for_frame(index: int, fps: int) -> int:
    return (index * 1000) // fps


def region_px(region: dict, width: int, height: int) -> tuple[int, int, int, int]:
    x = int(round(float(region["x"]) * width))
    y = int(round(float(region["y"]) * height))
    w = max(1, int(round(float(region["w"]) * width)))
    h = max(1, int(round(float(region["h"]) * height)))
    return x, y, w, h


def _active(prim: dict, local_ms: int) -> bool:
    start = int(prim["start_ms"])
    dur = int(prim["duration_ms"])
    if dur <= 0:
        return local_ms == start
    return start <= local_ms < start + dur


def _fit_image(src: Image.Image, box_w: int, box_h: int, crop_target: dict | None) -> Image.Image:
    img = src.convert("RGBA")
    if crop_target:
        x, y, w, h = region_px(crop_target, img.width, img.height)
        img = img.crop((x, y, x + w, y + h))
    sw, sh = img.size
    scale = max(box_w / sw, box_h / sh)
    nw, nh = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, (nw - box_w) // 2)
    top = max(0, (nh - box_h) // 2)
    return img.crop((left, top, left + box_w, top + box_h))


def _draws_raster(layer: dict) -> bool:
    types = [p.get("type") for p in layer.get("primitives") or []]
    if not types:
        return True
    return any(t in {"hold", "crop_9_16", "zoom_to_region", "pan_to_region"} for t in types)


def _lerp_region(a: dict, b: dict, e: float) -> dict:
    return {
        "x": float(a["x"]) + (float(b["x"]) - float(a["x"])) * e,
        "y": float(a["y"]) + (float(b["y"]) - float(a["y"])) * e,
        "w": float(a["w"]) + (float(b["w"]) - float(a["w"])) * e,
        "h": float(a["h"]) + (float(b["h"]) - float(a["h"])) * e,
    }


def zoom_crop(layer: dict, local_ms: int) -> dict | None:
    """Crop window on the source asset. After a zoom ends, stay on its target."""
    full = {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}
    base = full
    for prim in layer.get("primitives") or []:
        if prim.get("type") == "crop_9_16" and prim.get("target"):
            base = prim["target"]
            break
    chosen = None
    for prim in layer.get("primitives") or []:
        if prim.get("type") != "zoom_to_region":
            continue
        target = prim.get("target")
        if not target:
            raise RenderError("zoom_to_region missing target.")
        params = prim.get("params") or {}
        start_box = params.get("from") if isinstance(params.get("from"), dict) and "w" in params.get("from", {}) else base
        start = int(prim["start_ms"])
        dur = max(1, int(prim["duration_ms"]))
        if local_ms < start:
            continue
        if local_ms >= start + int(prim["duration_ms"]) and int(prim["duration_ms"]) > 0:
            chosen = target
            continue
        u = (local_ms - start) / dur
        e = _ease(u, str(params.get("easing") or prim.get("easing") or "linear"))
        chosen = _lerp_region(start_box, target, e)
    return chosen


def _same_scale(start: dict, target: dict) -> dict:
    """Translate to target x,y. Keep start w,h. Clamp into 0..1."""
    w = float(start["w"])
    h = float(start["h"])
    x = float(target["x"])
    y = float(target["y"])
    if x + w > 1:
        x = max(0.0, 1.0 - w)
    if y + h > 1:
        y = max(0.0, 1.0 - h)
    if x < 0:
        x = 0.0
    if y < 0:
        y = 0.0
    return {"x": x, "y": y, "w": w, "h": h}


def pan_crop(layer: dict, local_ms: int) -> dict | None:
    """Translate a fixed-size crop. After the pan ends, stay on the end box."""
    chosen = None
    for prim in layer.get("primitives") or []:
        if prim.get("type") != "pan_to_region":
            continue
        target = prim.get("target")
        if not target:
            raise RenderError("pan_to_region missing target.")
        params = prim.get("params") or {}
        start_box = params.get("from")
        if not isinstance(start_box, dict) or "w" not in start_box or "h" not in start_box:
            raise RenderError("pan_to_region needs params.from {x,y,w,h}.")
        end_box = _same_scale(start_box, target)
        start = int(prim["start_ms"])
        dur_raw = int(prim["duration_ms"])
        dur = max(1, dur_raw)
        if local_ms < start:
            continue
        if local_ms >= start + dur_raw and dur_raw > 0:
            chosen = end_box
            continue
        u = (local_ms - start) / dur
        e = _ease(u, str(params.get("easing") or prim.get("easing") or "linear"))
        chosen = _lerp_region(start_box, end_box, e)
    return chosen


def camera_crop(layer: dict, local_ms: int) -> dict | None:
    """Compose zoom then pan. Pan wins only when it has a crop (started).

    Zoom hold is used until the first pan frame so 1500 ms is continuous
    when pan.params.from equals the zoom target.
    """
    panned = pan_crop(layer, local_ms)
    if panned is not None:
        return panned
    return zoom_crop(layer, local_ms)


def _font(size: int) -> ImageFont.FreeTypeFont:
    if DEFAULT_FONT.is_file():
        return ImageFont.truetype(str(DEFAULT_FONT), size)
    return ImageFont.load_default()


def _draw_highlight(canvas: Image.Image, prim: dict, width: int, height: int) -> None:
    target = prim.get("target")
    if not target:
        raise RenderError("highlight_box missing target.")
    x, y, w, h = region_px(target, width, height)
    params = prim.get("params") or {}
    stroke = int(params.get("stroke_px", HIGHLIGHT_STROKE))
    color = tuple(params.get("color", HIGHLIGHT_COLOR[:3])) + (int(params.get("opacity", HIGHLIGHT_COLOR[3])),)
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([x, y, x + w, y + h], outline=color, width=max(1, stroke))
    canvas.alpha_composite(overlay)


def _draw_spotlight(canvas: Image.Image, prim: dict, width: int, height: int) -> None:
    target = prim.get("target")
    if not target:
        raise RenderError("spotlight_dim missing target.")
    x, y, w, h = region_px(target, width, height)
    params = prim.get("params") or {}
    dim = float(params.get("dim", SPOT_DEFAULT))
    if dim < 0 or dim > 1:
        raise RenderError("spotlight_dim params.dim must be in 0..1.")
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, int(round(255 * dim))))
    ImageDraw.Draw(overlay).rectangle([x, y, x + w, y + h], fill=(0, 0, 0, 0))
    canvas.alpha_composite(overlay)


def _point(params_key: dict | None) -> tuple[float, float] | None:
    if not isinstance(params_key, dict):
        return None
    if "x" not in params_key or "y" not in params_key:
        return None
    return float(params_key["x"]), float(params_key["y"])


def _ease(u: float, name: str) -> float:
    u = 0.0 if u < 0 else 1.0 if u > 1 else u
    if name == "ease_in":
        return u * u
    if name == "ease_out":
        return 1.0 - (1.0 - u) * (1.0 - u)
    if name == "ease_in_out":
        return 2 * u * u if u < 0.5 else 1.0 - ((-2 * u + 2) ** 2) / 2
    return u


def cursor_pos(prim: dict, local_ms: int) -> tuple[float, float]:
    """Normalized cursor hot-spot. cursor_move interpolates; cursor_click is static."""
    params = prim.get("params") or {}
    ptype = prim.get("type")
    if ptype == "cursor_click":
        pos = _point(params.get("position"))
        if pos:
            return pos
        if "target" in prim:
            t = prim["target"]
            return float(t["x"]) + float(t["w"]) / 2, float(t["y"]) + float(t["h"]) / 2
        raise RenderError("cursor_click needs params.position or target.")
    start = int(prim["start_ms"])
    dur = max(1, int(prim["duration_ms"]))
    u = (local_ms - start) / dur
    easing = params.get("easing") or prim.get("easing") or "linear"
    e = _ease(u, str(easing))
    frm = _point(params.get("from"))
    to = _point(params.get("to"))
    if to is None and "target" in prim:
        t = prim["target"]
        to = (float(t["x"]) + float(t["w"]) / 2, float(t["y"]) + float(t["h"]) / 2)
    if frm is None:
        frm = to
    if frm is None or to is None:
        raise RenderError("cursor_move needs params.from/to or target.")
    return frm[0] + (to[0] - frm[0]) * e, frm[1] + (to[1] - frm[1]) * e


def _draw_cursor_arrow(overlay: Image.Image, x: int, y: int, scale: float = 1.0) -> None:
    """Hot-spot is the tip. White fill, dark outline. Not an OS cursor."""
    s = max(0.6, scale)
    pts = [
        (x, y),
        (x + int(18 * s), y + int(28 * s)),
        (x + int(11 * s), y + int(28 * s)),
        (x + int(16 * s), y + int(46 * s)),
        (x + int(10 * s), y + int(46 * s)),
        (x + int(6 * s), y + int(28 * s)),
        (x, y + int(28 * s)),
    ]
    draw = ImageDraw.Draw(overlay)
    draw.polygon(pts, fill=(255, 255, 255, 255), outline=(20, 24, 30, 255))


def _draw_cursor_move(canvas: Image.Image, prim: dict, local_ms: int, width: int, height: int) -> None:
    nx, ny = cursor_pos(prim, local_ms)
    x, y = int(round(nx * width)), int(round(ny * height))
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    _draw_cursor_arrow(overlay, x, y)
    canvas.alpha_composite(overlay)


def _draw_cursor_click(canvas: Image.Image, prim: dict, local_ms: int, width: int, height: int) -> None:
    nx, ny = cursor_pos(prim, local_ms)
    x, y = int(round(nx * width)), int(round(ny * height))
    start = int(prim["start_ms"])
    dur = max(1, int(prim["duration_ms"]))
    elapsed = local_ms - start
    u = elapsed / dur
    radius = int(round(10 + 22 * u))
    alpha = max(0, int(200 * (1.0 - u)))
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    box = [x - radius, y - radius, x + radius, y + radius]
    draw.ellipse(box, outline=(255, 255, 255, alpha), width=3)
    inner = [x - radius + 6, y - radius + 6, x + radius - 6, y + radius - 6]
    if inner[2] > inner[0] and inner[3] > inner[1]:
        draw.ellipse(inner, outline=(255, 214, 0, alpha), width=2)
    _draw_cursor_arrow(overlay, x, y, scale=1.0 + 0.12 * (1.0 - u) if u < 0.45 else 1.0)
    canvas.alpha_composite(overlay)


def _draw_text(canvas: Image.Image, prim: dict, cue_text: str | None, local_ms: int, width: int, height: int) -> None:
    params = prim.get("params") or {}
    text = params.get("text") or cue_text
    if not text:
        raise RenderError("kinetic_text needs params.text or params.from_cue_id.")
    size = int(params.get("font_size", 42))
    font = _font(size)
    fade_ms = int(params.get("fade_ms", TEXT_FADE_MS))
    elapsed = local_ms - int(prim["start_ms"])
    if fade_ms <= 0:
        alpha = 255
    else:
        alpha = min(255, max(0, elapsed * 255 // fade_ms))
    if "target" in prim:
        x, y, w, h = region_px(prim["target"], width, height)
        anchor_x, anchor_y = x + w // 2, y + h // 2
    else:
        anchor_x, anchor_y = width // 2, int(round(0.78 * height))
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    fill = tuple(params.get("color", (255, 255, 255))) + (alpha,)
    shadow = (0, 0, 0, min(200, alpha))
    draw.text((anchor_x + 2, anchor_y + 2), text, font=font, fill=shadow, anchor="mm")
    draw.text((anchor_x, anchor_y), text, font=font, fill=fill, anchor="mm")
    canvas.alpha_composite(overlay)


def compose_frame(project: dict, assets: dict, project_path: Path, time_ms: int) -> Image.Image:
    width, height = int(project["width"]), int(project["height"])
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    scene = None
    for sc in project["scenes"]:
        a, b = int(sc["start_ms"]), int(sc["start_ms"]) + int(sc["duration_ms"])
        if a <= time_ms < b:
            scene = sc
            break
    if scene is None:
        return canvas.convert("RGB")
    local = time_ms - int(scene["start_ms"])
    layers = sorted(scene["layers"], key=lambda ly: int(ly.get("z_index", 0)))
    cues = {c["cue_id"]: c.get("text") for c in scene.get("cues") or [] if "cue_id" in c}

    for layer in layers:
        vis = layer.get("visibility") or {}
        vf = int(vis.get("from_ms", 0))
        vt = int(vis["to_ms"]) if "to_ms" in vis else int(scene["duration_ms"])
        if not (vf <= local < vt):
            continue
        if _draws_raster(layer):
            img = Image.open(require_image_file(assets[layer["asset_id"]], project_path))
            crop_t = None
            for p in layer.get("primitives") or []:
                if p.get("type") == "crop_9_16":
                    crop_t = p.get("target")
                    break
            composed = camera_crop(layer, local)
            if composed is not None:
                crop_t = composed
            tf = layer["transform"]
            bx, by, bw, bh = region_px(tf, width, height)
            fitted = _fit_image(img, bw, bh, crop_t)
            if tf.get("opacity", 1.0) < 1:
                fitted = fitted.copy()
                a = fitted.split()[3].point(lambda v: int(v * float(tf.get("opacity", 1.0))))
                fitted.putalpha(a)
            canvas.paste(fitted, (bx, by), fitted)
        for prim in layer.get("primitives") or []:
            if prim.get("type") not in SUPPORTED:
                raise RenderError(f"Unsupported primitive '{prim.get('type')}'.")
            if not _active(prim, local):
                continue
            ptype = prim["type"]
            if ptype == "highlight_box":
                _draw_highlight(canvas, prim, width, height)
            elif ptype == "spotlight_dim":
                _draw_spotlight(canvas, prim, width, height)
            elif ptype == "kinetic_text":
                cue_id = (prim.get("params") or {}).get("from_cue_id")
                _draw_text(canvas, prim, cues.get(cue_id), local, width, height)
            elif ptype == "cursor_move":
                _draw_cursor_move(canvas, prim, local, width, height)
            elif ptype == "cursor_click":
                _draw_cursor_click(canvas, prim, local, width, height)
    return canvas.convert("RGB")
