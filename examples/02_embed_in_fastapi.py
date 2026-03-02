"""
Embedding the IIIF router into an existing FastAPI application.

The IIIF endpoints are mounted at /iiif, while the rest of the application
keeps its own routes. CORS is managed by the host application, not by sanf.

Run with:
    uvicorn examples.02_embed_in_fastapi:app --reload
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sanf import IIIFServerSettings, LocalFileConnector, create_iiif_router

app = FastAPI(title="My Application")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://viewer.example.com"],
    allow_methods=["GET"],
)

settings = IIIFServerSettings(
    connector=LocalFileConnector(root=Path("./images")),
)
app.include_router(create_iiif_router(settings), prefix="/iiif")


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
