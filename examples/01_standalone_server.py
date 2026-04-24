"""
Standalone IIIF server.

Run with:
    uvicorn examples.01_standalone_server:app --reload

Or using the built-in factory shorthand:
    IIIF_SOURCE_ROOT=./images uvicorn sanf.main:create_app --factory --reload
"""

from pathlib import Path

from sanf import IIIFServerSettings, LocalFileConnector, create_app

settings = IIIFServerSettings(
    connector=LocalFileConnector(root=Path("./images")),
)

app = create_app(settings)
