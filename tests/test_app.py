from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

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
