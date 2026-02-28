from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import re

from PIL import Image


class IIIFRequestError(ValueError):
    pass


@dataclass(slots=True)
class ImageTransform:
    left: int
    top: int
    width: int
    height: int
    output_width: int
    output_height: int


_REGION_RE = re.compile(r"^(\d+),(\d+),(\d+),(\d+)$")
_SIZE_W_RE = re.compile(r"^(\d+),$")
_SIZE_H_RE = re.compile(r"^,(\d+)$")


def parse_region(region: str, width: int, height: int) -> tuple[int, int, int, int]:
    if region == "full":
        return 0, 0, width, height

    if region == "square":
        edge = min(width, height)
        left = (width - edge) // 2
        top = (height - edge) // 2
        return left, top, edge, edge

    match = _REGION_RE.fullmatch(region)
    if not match:
        raise IIIFRequestError("unsupported region")

    left, top, region_w, region_h = (int(match.group(i)) for i in range(1, 5))
    if region_w <= 0 or region_h <= 0:
        raise IIIFRequestError("region width/height must be > 0")
    if left < 0 or top < 0 or left + region_w > width or top + region_h > height:
        raise IIIFRequestError("region is out of bounds")

    return left, top, region_w, region_h


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

    raise IIIFRequestError("unsupported size")


def validate_rotation(rotation: str) -> None:
    if rotation != "0":
        raise IIIFRequestError("unsupported rotation")


def validate_quality_and_format(quality: str, fmt: str) -> None:
    if quality != "default":
        raise IIIFRequestError("unsupported quality")
    if fmt != "jpg":
        raise IIIFRequestError("unsupported format")


def render_jpeg(source_bytes: bytes, region: str, size: str, rotation: str) -> tuple[bytes, int, int]:
    validate_rotation(rotation)

    with Image.open(BytesIO(source_bytes)) as image:
        rgb = image.convert("RGB")
        left, top, crop_w, crop_h = parse_region(region, rgb.width, rgb.height)
        out_w, out_h = parse_size(size, crop_w, crop_h)

        cropped = rgb.crop((left, top, left + crop_w, top + crop_h))
        if (out_w, out_h) != (crop_w, crop_h):
            cropped = cropped.resize((out_w, out_h), Image.Resampling.LANCZOS)

        output = BytesIO()
        cropped.save(output, format="JPEG", quality=85)
        return output.getvalue(), rgb.width, rgb.height
