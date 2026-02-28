from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from PIL import Image

from app.connectors import ConnectorError, ImageNotFoundError, ImageSourceConnector, LocalFileConnector
from app.iiif import IIIFRequestError, _MEDIA_TYPE, render_image, validate_quality_and_format


IIIF_PROTOCOL = "http://iiif.io/api/image"
IIIF_LEVEL = "level1"


class ServiceContainer:
    def __init__(self, connector: ImageSourceConnector):
        self.connector = connector


app = FastAPI(title="Serverless IIIF Image Server", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


def _default_connector() -> ImageSourceConnector:
    root = Path(os.getenv("IIIF_SOURCE_ROOT", "./images"))
    return LocalFileConnector(root=root)


app.state.services = ServiceContainer(connector=_default_connector())


def _read_image(identifier: str, request: Request) -> bytes:
    if not identifier or identifier.endswith("/"):
        raise HTTPException(status_code=400, detail="invalid identifier")

    connector: ImageSourceConnector = request.app.state.services.connector
    try:
        return connector.fetch_image_bytes(identifier)
    except ImageNotFoundError as exc:
        raise HTTPException(status_code=404, detail="identifier not found") from exc
    except ConnectorError as exc:
        raise HTTPException(status_code=502, detail="connector error") from exc


def _service_id(request: Request, identifier: str) -> str:
    return str(request.url_for("iiif_base", identifier=identifier))


@app.get("/iiif/{identifier}", name="iiif_base")
def iiif_base(identifier: str, request: Request) -> RedirectResponse:
    return RedirectResponse(url=str(request.url_for("iiif_info", identifier=identifier)), status_code=303)


@app.get("/iiif/{identifier}/info.json", name="iiif_info")
def iiif_info(identifier: str, request: Request) -> JSONResponse:
    data = _read_image(identifier, request)

    with Image.open(BytesIO(data)) as image:
        width, height = image.size

    body = {
        "@context": "http://iiif.io/api/image/3/context.json",
        "id": _service_id(request, identifier),
        "type": "ImageService3",
        "protocol": IIIF_PROTOCOL,
        "profile": IIIF_LEVEL,
        "width": width,
        "height": height,
        "extraQualities": ["default"],
        "extraFormats": ["jpg", "png"],
    }
    return JSONResponse(body, media_type="application/ld+json")


@app.get("/iiif/{identifier}/{region}/{size}/{rotation}/{quality_format}")
def iiif_image(
    identifier: str,
    region: str,
    size: str,
    rotation: str,
    quality_format: str,
    request: Request,
) -> Response:
    try:
        quality, fmt = quality_format.rsplit(".", 1)
        identifier_with_fmt = identifier + "." + fmt
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="quality.format must be provided") from exc

    validate_quality_and_format(quality, fmt)
    source = _read_image(identifier_with_fmt, request)

    try:
        rendered, _, _ = render_image(source, region=region, size=size, rotation=rotation, fmt=fmt)
    except IIIFRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(content=rendered, media_type=_MEDIA_TYPE[fmt])


@app.exception_handler(IIIFRequestError)
def iiif_error_handler(_: Request, exc: IIIFRequestError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})
