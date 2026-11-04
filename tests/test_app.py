from __future__ import annotations

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image, JpegImagePlugin

from sanf.connectors import ImageNotFoundError
from sanf import create_app, IIIFServerSettings


class InMemoryConnector:
    def __init__(self, items: dict[str, bytes]):
        self.items = items

    def fetch_image_bytes(self, identifier: str) -> bytes:
        if identifier not in self.items:
            raise ImageNotFoundError(identifier)
        return self.items[identifier]


def _make_image(width: int = 200, height: int = 100) -> bytes:
    image = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue()


def _client() -> TestClient:
    settings = IIIFServerSettings(connector=InMemoryConnector({"sample": _make_image()}))
    return TestClient(create_app(settings))


def _response_size(response) -> tuple[int, int]:
    with Image.open(BytesIO(response.content)) as image:
        return image.size


def test_info_json() -> None:
    client = _client()
    response = client.get("/iiif/sample/info.json")

    assert response.status_code == 200
    body = response.json()
    assert body["profile"] == "level2"
    assert body["width"] == 200
    assert body["height"] == 100


def test_image_full_max_default_jpg() -> None:
    client = _client()
    response = client.get("/iiif/sample/full/max/0/default.jpg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/jpeg")


def test_level1_region_and_size() -> None:
    client = _client()
    response = client.get("/iiif/sample/0,0,100,100/50,/0/default.jpg")

    assert response.status_code == 200


def test_level2_pct_region_and_pct_size() -> None:
    client = _client()
    response = client.get("/iiif/sample/pct:0,0,50,50/pct:50/0/default.jpg")

    assert response.status_code == 200
    assert _response_size(response) == (50, 25)


def test_level2_exact_size_png() -> None:
    client = _client()
    response = client.get("/iiif/sample/full/80,40/0/default.png")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert _response_size(response) == (80, 40)


def test_level2_best_fit_size() -> None:
    client = _client()
    response = client.get("/iiif/sample/full/!80,80/0/default.jpg")

    assert response.status_code == 200
    assert _response_size(response) == (80, 40)


def test_level2_rotation_90() -> None:
    client = _client()
    response = client.get("/iiif/sample/full/max/90/default.jpg")

    assert response.status_code == 200
    assert _response_size(response) == (100, 200)


def test_arbitrary_rotation_is_valid() -> None:
    client = _client()
    response = client.get("/iiif/sample/full/max/45/default.jpg")

    assert response.status_code == 200


def test_invalid_rotation() -> None:
    client = _client()
    response = client.get("/iiif/sample/full/max/-90/default.jpg")

    assert response.status_code == 400


def test_info_json_id_uses_request_url_by_default() -> None:
    client = _client()
    response = client.get("/iiif/sample/info.json")

    assert response.status_code == 200
    body = response.json()
    assert body["id"].startswith("http://testserver/iiif/sample")


def test_info_json_id_overridden_by_public_base_url() -> None:
    settings = IIIFServerSettings(
        connector=InMemoryConnector({"sample": _make_image()}),
        public_base_url="https://proxy.example.com",
    )
    client = TestClient(create_app(settings))
    response = client.get("/iiif/sample/info.json")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "https://proxy.example.com/iiif/sample"


def test_info_json_id_public_base_url_trailing_slash_normalized() -> None:
    settings = IIIFServerSettings(
        connector=InMemoryConnector({"sample": _make_image()}),
        public_base_url="https://proxy.example.com/",
    )
    client = TestClient(create_app(settings))
    response = client.get("/iiif/sample/info.json")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "https://proxy.example.com/iiif/sample"


def _encode(image: Image.Image, fmt: str) -> bytes:
    buf = BytesIO()
    image.save(buf, format=fmt)
    return buf.getvalue()


def _render_client(items: dict[str, bytes], **kwargs) -> TestClient:
    return TestClient(create_app(IIIFServerSettings(connector=InMemoryConnector(items), **kwargs)))


def test_grayscale_source_is_rendered_without_conversion() -> None:
    gray = Image.new("L", (200, 100), color=128)
    client = _render_client({"gray": _encode(gray, "JPEG")})

    for path in ("full/max/0/default.jpg", "0,0,100,100/50,/90/default.png"):
        response = client.get(f"/iiif/gray/{path}")
        assert response.status_code == 200
        with Image.open(BytesIO(response.content)) as image:
            assert image.mode == "L"


def test_non_rgb_sources_are_converted() -> None:
    rgba = Image.new("RGBA", (200, 100), color=(0, 255, 0, 128))
    palette = Image.new("RGB", (200, 100), color=(0, 0, 255)).convert("P")
    client = _render_client({"rgba": _encode(rgba, "PNG"), "palette": _encode(palette, "PNG")})

    for identifier in ("rgba", "palette"):
        for fmt in ("jpg", "png"):
            response = client.get(f"/iiif/{identifier}/full/50,/0/default.{fmt}")
            assert response.status_code == 200
            with Image.open(BytesIO(response.content)) as image:
                assert image.mode == "RGB"
                assert image.size == (50, 25)


QUADRANT_COLORS = {
    "top_left": (255, 0, 0),
    "top_right": (0, 255, 0),
    "bottom_left": (0, 0, 255),
    "bottom_right": (255, 255, 0),
}


def _quadrant_jpeg(width: int = 2000, height: int = 1600) -> bytes:
    image = Image.new("RGB", (width, height))
    half_w, half_h = width // 2, height // 2
    image.paste(QUADRANT_COLORS["top_left"], (0, 0, half_w, half_h))
    image.paste(QUADRANT_COLORS["top_right"], (half_w, 0, width, half_h))
    image.paste(QUADRANT_COLORS["bottom_left"], (0, half_h, half_w, height))
    image.paste(QUADRANT_COLORS["bottom_right"], (half_w, half_h, width, height))
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def _assert_color(response, expected: tuple[int, int, int], tolerance: int = 24) -> None:
    with Image.open(BytesIO(response.content)) as image:
        rgb = image.convert("RGB")
        # Ignore a 2px border where JPEG/resampling may blend with neighbours.
        inner = rgb.crop((2, 2, rgb.width - 2, rgb.height - 2)) if min(rgb.size) > 8 else rgb
        for channel, value in zip(inner.split(), expected):
            low, high = channel.getextrema()
            assert value - tolerance <= low and high <= value + tolerance, (expected, low, high)


@pytest.mark.parametrize(
    ("region", "size", "expected"),
    [
        ("full", "max", (2000, 1600)),
        ("full", "250,", (250, 200)),
        ("full", "!100,100", (100, 80)),
        ("full", "pct:12.5", (250, 200)),
        ("0,0,1000,800", "125,100", (125, 100)),
        ("1000,800,1000,800", ",100", (125, 100)),
        ("1999,1599,10,10", "max", (1, 1)),
        ("1500,0,600,600", "50,", (50, 60)),
        ("pct:50,0,50,50", "pct:5", (50, 40)),
        ("0,0,100,80", "400,", (400, 320)),
        ("square", "!64,64", (64, 64)),
    ],
)
def test_output_size_with_jpeg_dct_scaling(region: str, size: str, expected: tuple[int, int]) -> None:
    client = _render_client({"page": _quadrant_jpeg()})
    response = client.get(f"/iiif/page/{region}/{size}/0/default.png")

    assert response.status_code == 200
    assert _response_size(response) == expected


@pytest.mark.parametrize(
    ("region", "quadrant"),
    [
        ("0,0,1000,800", "top_left"),
        ("1000,0,1000,800", "top_right"),
        ("0,800,1000,800", "bottom_left"),
        ("1000,800,1000,800", "bottom_right"),
        ("1100,900,700,500", "bottom_right"),
        ("pct:5,55,40,40", "bottom_left"),
    ],
)
@pytest.mark.parametrize("size", ["max", "500,", "125,", "40,"])
def test_region_maps_correctly_with_jpeg_dct_scaling(region: str, quadrant: str, size: str) -> None:
    client = _render_client({"page": _quadrant_jpeg()})
    response = client.get(f"/iiif/page/{region}/{size}/0/default.png")

    assert response.status_code == 200
    _assert_color(response, QUADRANT_COLORS[quadrant])


@pytest.mark.parametrize(
    ("region", "size", "expected_scale"),
    [
        ("full", "max", 1),
        ("full", "1000,", 2),
        ("full", "500,", 4),
        ("full", "250,", 8),
        ("full", "100,", 8),
        ("full", "251,", 4),
        ("0,0,1000,800", "max", 1),
        ("0,0,1000,800", "250,", 4),
        ("0,0,100,100", "200,", 1),
    ],
)
def test_jpeg_decoder_scale(monkeypatch, region: str, size: str, expected_scale: int) -> None:
    scales: list[int] = []
    original_draft = JpegImagePlugin.JpegImageFile.draft

    def spy(self, mode, requested):
        result = original_draft(self, mode, requested)
        scales.append(self.decoderconfig[0] if self.decoderconfig else 1)
        return result

    monkeypatch.setattr(JpegImagePlugin.JpegImageFile, "draft", spy)
    client = _render_client({"page": _quadrant_jpeg()})
    response = client.get(f"/iiif/page/{region}/{size}/0/default.jpg")

    assert response.status_code == 200
    assert scales == [expected_scale]


def test_max_width_limits_output_with_jpeg_dct_scaling() -> None:
    client = _render_client({"page": _quadrant_jpeg()}, max_width=300)
    response = client.get("/iiif/page/full/max/0/default.png")

    assert response.status_code == 200
    assert _response_size(response) == (300, 240)
