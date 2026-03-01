from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.routing import APIRouter
from PIL import Image

from sanf.connectors import ConnectorError, ImageNotFoundError, LocalFileConnector
from sanf.iiif import IIIFRequestError, MEDIA_TYPE, render_image, validate_quality_and_format
from sanf.settings import IIIFServerSettings


IIIF_PROTOCOL = "http://iiif.io/api/image"
IIIF_LEVEL = "level2"


def create_iiif_router(settings: IIIFServerSettings) -> APIRouter:
    router = APIRouter()

    def _get_image_bytes(identifier: str) -> bytes:
        if not identifier or identifier.endswith("/"):
            raise HTTPException(status_code=400, detail="invalid identifier")
        try:
            return settings.connector.fetch_image_bytes(identifier)
        except ImageNotFoundError as exc:
            raise HTTPException(status_code=404, detail="identifier not found") from exc
        except ConnectorError as exc:
            raise HTTPException(status_code=502, detail="connector error") from exc

    def _service_id(request: Request, identifier: str) -> str:
        return str(request.url_for("iiif_base", identifier=identifier))

    @router.get("/{identifier}", name="iiif_base")
    def iiif_base(identifier: str, request: Request) -> RedirectResponse:
        return RedirectResponse(url=str(request.url_for("iiif_info", identifier=identifier)), status_code=303)

    @router.get("/{identifier}/info.json", name="iiif_info")
    def iiif_info(identifier: str, request: Request) -> JSONResponse:
        data = _get_image_bytes(identifier)

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

    @router.get("/{identifier}/{region}/{size}/{rotation}/{quality_format}")
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
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="quality.format must be provided") from exc

        validate_quality_and_format(quality, fmt)
        source = _get_image_bytes(identifier)

        try:
            rendered, _, _ = render_image(
                source,
                region=region,
                size=size,
                rotation=rotation,
                fmt=fmt,
                jpeg_quality=settings.jpeg_quality,
                max_width=settings.max_width,
                max_height=settings.max_height,
            )
        except IIIFRequestError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return Response(content=rendered, media_type=MEDIA_TYPE[fmt])

    return router


def create_app(settings: IIIFServerSettings | None = None) -> FastAPI:
    if settings is None:
        settings = IIIFServerSettings(
            connector=LocalFileConnector(Path(os.getenv("IIIF_SOURCE_ROOT", "./images")))
        )

    application = FastAPI(title="Serverless IIIF Image Server", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )
    application.include_router(create_iiif_router(settings), prefix="/iiif")
    return application


app = create_app
