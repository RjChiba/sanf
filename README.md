# SanF

A [IIIF Image API 3.0](https://iiif.io/api/image/3.0/) server implementation built with FastAPI, supporting up to **Level 2** compliance.
It can be used as a standalone server or embedded as a package within an existing FastAPI application.

## Features

- `GET /iiif/{identifier}/info.json`
- `GET /iiif/{identifier}/{region}/{size}/{rotation}/{quality}.{format}`
- 303 redirect from `GET /iiif/{identifier}` to `info.json`
- Level 2 parameters:
  - `region`: `full`, `square`, `x,y,w,h`, `pct:x,y,w,h`
  - `size`: `max`, `w,`, `,h`, `pct:n`, `w,h`, `!w,h`
  - `rotation`: `0`, `90`, `180`, `270` (and arbitrary non-negative angles)
  - `quality`: `default`
  - `format`: `jpg`, `png`
- CORS enabled (when using `create_app`, default `*`)

## Installation

```bash
pip install sanf
```

## Development Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Running as a Standalone Server

Source images are loaded from `./images` by default.

```bash
uvicorn sanf.main:create_app --factory --reload
```

The root directory for the local file connector can be changed via the `IIIF_SOURCE_ROOT` environment variable.

```bash
IIIF_SOURCE_ROOT=/path/to/images uvicorn sanf.main:create_app --factory --reload
```

## Using as a Package

### Public API

| Symbol | Purpose |
|---|---|
| `IIIFServerSettings` | Settings dataclass |
| `create_app(settings)` | Creates a standalone `FastAPI` application |
| `create_iiif_router(settings)` | Creates an `APIRouter` for embedding into an existing application |
| `ImageSourceConnector` | Protocol definition for connectors |
| `LocalFileConnector` | Connector for local filesystem images |
| `ConnectorError` / `ImageNotFoundError` | Connector exceptions |

### `IIIFServerSettings`

```python
from sanf import IIIFServerSettings, LocalFileConnector
from pathlib import Path

settings = IIIFServerSettings(
    connector=LocalFileConnector(root=Path("./images")),
    cors_origins=["https://example.com"],   # default: ["*"]
    jpeg_quality=85,                         # default: 85
    max_width=4096,                          # default: None (no limit)
    max_height=4096,                         # default: None (no limit)
)
```

### `create_app` — Standalone Application

Returns a complete `FastAPI` instance including CORS middleware.

```python
from sanf import create_app, IIIFServerSettings, LocalFileConnector
from pathlib import Path

settings = IIIFServerSettings(connector=LocalFileConnector(root=Path("./images")))
app = create_app(settings)
```

### `create_iiif_router` — Embedding into an Existing Application

Returns an `APIRouter` without CORS. CORS should be managed by the calling application.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sanf import create_iiif_router, IIIFServerSettings, LocalFileConnector
from pathlib import Path

settings = IIIFServerSettings(connector=LocalFileConnector(root=Path("./images")))

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])
app.include_router(create_iiif_router(settings), prefix="/iiif")
```

## Custom Connectors

Any storage backend can be connected by implementing a class that conforms to the `ImageSourceConnector` protocol.

```python
class MyS3Connector:
    def fetch_image_bytes(self, identifier: str) -> bytes:
        # Return image bytes from S3 or any other backend
        ...
```

- Raise `ImageNotFoundError` when the identifier does not exist
- Raise `ConnectorError` for backend failures
- The `identifier` is received as a URL-decoded string
