from __future__ import annotations

from io import BytesIO
import re

from PIL import Image


class IIIFRequestError(ValueError):
    pass


_REGION_RE = re.compile(r"^(\d+),(\d+),(\d+),(\d+)$")
_REGION_PCT_RE = re.compile(r"^pct:(\d+(?:\.\d+)?),(\d+(?:\.\d+)?),(\d+(?:\.\d+)?),(\d+(?:\.\d+)?)$")
_SIZE_W_RE = re.compile(r"^(\d+),$")
_SIZE_H_RE = re.compile(r"^,(\d+)$")
_SIZE_PCT_RE = re.compile(r"^pct:(\d+(?:\.\d+)?)$")
_SIZE_WH_RE = re.compile(r"^(\d+),(\d+)$")
_SIZE_BEST_FIT_RE = re.compile(r"^!(\d+),(\d+)$")


def parse_region(region: str, width: int, height: int) -> tuple[int, int, int, int]:
    if region == "full":
        return 0, 0, width, height

    if region == "square":
        edge = min(width, height)
        left = (width - edge) // 2
        top = (height - edge) // 2
        return left, top, edge, edge

    match = _REGION_RE.fullmatch(region)
    if match:
        left, top, region_w, region_h = (int(match.group(i)) for i in range(1, 5))
        if region_w <= 0 or region_h <= 0:
            raise IIIFRequestError("region width/height must be > 0")
        if left >= width or top >= height:
            raise IIIFRequestError("region origin is out of bounds")
        # Clip to image boundary per IIIF spec
        region_w = min(region_w, width - left)
        region_h = min(region_h, height - top)
        return left, top, region_w, region_h

    pct_match = _REGION_PCT_RE.fullmatch(region)
    if not pct_match:
        raise IIIFRequestError("unsupported region")

    x_pct, y_pct, w_pct, h_pct = (float(pct_match.group(i)) for i in range(1, 5))
    if w_pct <= 0 or h_pct <= 0:
        raise IIIFRequestError("region width/height must be > 0")
    if x_pct >= 100 or y_pct >= 100:
        raise IIIFRequestError("region origin is out of bounds")

    left = round(width * (x_pct / 100.0))
    top = round(height * (y_pct / 100.0))
    # Clip to image boundary per IIIF spec
    region_w = max(1, min(round(width * (w_pct / 100.0)), width - left))
    region_h = max(1, min(round(height * (h_pct / 100.0)), height - top))

    return left, top, region_w, region_h


def _scale_to_best_fit(region_w: int, region_h: int, max_w: int, max_h: int) -> tuple[int, int]:
    ratio = min(max_w / region_w, max_h / region_h)
    return max(1, round(region_w * ratio)), max(1, round(region_h * ratio))


def parse_size(size: str, region_w: int, region_h: int) -> tuple[int, int]:
    if size == "max":
        return region_w, region_h

    w_match = _SIZE_W_RE.fullmatch(size)
    if w_match:
        target_w = int(w_match.group(1))
        if target_w <= 0:
            raise IIIFRequestError("width must be > 0")
        target_h = max(1, round(region_h * (target_w / region_w)))
        return target_w, target_h

    h_match = _SIZE_H_RE.fullmatch(size)
    if h_match:
        target_h = int(h_match.group(1))
        if target_h <= 0:
            raise IIIFRequestError("height must be > 0")
        target_w = max(1, round(region_w * (target_h / region_h)))
        return target_w, target_h

    pct_match = _SIZE_PCT_RE.fullmatch(size)
    if pct_match:
        pct = float(pct_match.group(1))
        if pct <= 0:
            raise IIIFRequestError("size pct must be > 0")
        return max(1, round(region_w * (pct / 100.0))), max(1, round(region_h * (pct / 100.0)))

    wh_match = _SIZE_WH_RE.fullmatch(size)
    if wh_match:
        target_w, target_h = int(wh_match.group(1)), int(wh_match.group(2))
        if target_w <= 0 or target_h <= 0:
            raise IIIFRequestError("width/height must be > 0")
        return target_w, target_h

    best_fit_match = _SIZE_BEST_FIT_RE.fullmatch(size)
    if best_fit_match:
        max_w, max_h = int(best_fit_match.group(1)), int(best_fit_match.group(2))
        if max_w <= 0 or max_h <= 0:
            raise IIIFRequestError("width/height must be > 0")
        return _scale_to_best_fit(region_w, region_h, max_w, max_h)

    raise IIIFRequestError("unsupported size")


def validate_rotation(rotation: str) -> None:
    if rotation not in {"0", "90", "180", "270"}:
        raise IIIFRequestError("unsupported rotation")


_SUPPORTED_FORMATS = {"jpg", "png"}
_PIL_FORMAT = {"jpg": "JPEG", "png": "PNG"}
_MEDIA_TYPE = {"jpg": "image/jpeg", "png": "image/png"}


def validate_quality_and_format(quality: str, fmt: str) -> None:
    if quality != "default":
        raise IIIFRequestError("unsupported quality")
    if fmt not in _SUPPORTED_FORMATS:
        raise IIIFRequestError("unsupported format")


def render_image(source_bytes: bytes, region: str, size: str, rotation: str, fmt: str) -> tuple[bytes, int, int]:
    validate_rotation(rotation)

    with Image.open(BytesIO(source_bytes)) as image:
        rgb = image.convert("RGB")
        left, top, crop_w, crop_h = parse_region(region, rgb.width, rgb.height)
        out_w, out_h = parse_size(size, crop_w, crop_h)

        cropped = rgb.crop((left, top, left + crop_w, top + crop_h))
        if (out_w, out_h) != (crop_w, crop_h):
            cropped = cropped.resize((out_w, out_h), Image.Resampling.LANCZOS)
        if rotation != "0":
            cropped = cropped.rotate(-int(rotation), expand=True)

        output = BytesIO()
        save_kwargs: dict = {"format": _PIL_FORMAT[fmt]}
        if fmt == "jpg":
            save_kwargs["quality"] = 85
        cropped.save(output, **save_kwargs)
        return output.getvalue(), rgb.width, rgb.height
