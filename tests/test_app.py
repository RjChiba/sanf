from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.connectors import ImageNotFoundError
from app.main import ServiceContainer, app


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
    app.state.services = ServiceContainer(connector=InMemoryConnector({"sample": _make_image()}))
    return TestClient(app)


def test_info_json() -> None:
    client = _client()
    response = client.get("/iiif/sample/info.json")

    assert response.status_code == 200
    body = response.json()
    assert body["profile"] == "level1"
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


def test_invalid_rotation() -> None:
    client = _client()
    response = client.get("/iiif/sample/full/max/90/default.jpg")

    assert response.status_code == 400
