# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-03-01

### Added
- Initial public release of SanF, a IIIF Image API 3.0 server built with FastAPI.
- `create_app(settings)` — creates a standalone FastAPI application with CORS middleware.
- `create_iiif_router(settings)` — creates an `APIRouter` for embedding into an existing FastAPI application.
- `IIIFServerSettings` — settings dataclass with connector, CORS origins, JPEG quality, and max dimension options.
- `LocalFileConnector` — filesystem-based image source connector with path traversal protection.
- `ImageSourceConnector` protocol — allows custom storage backends (S3, database, etc.).
- `ConnectorError` / `ImageNotFoundError` — structured exceptions for connector implementations.
- IIIF Image API 3.0 Level 2 compliance:
  - `GET /iiif/{identifier}/info.json`
  - `GET /iiif/{identifier}/{region}/{size}/{rotation}/{quality}.{format}`
  - `GET /iiif/{identifier}` → 303 redirect to `info.json`
  - Region: `full`, `square`, `x,y,w,h`, `pct:x,y,w,h`
  - Size: `max`, `w,`, `,h`, `pct:n`, `w,h`, `!w,h`
  - Rotation: `0`, `90`, `180`, `270`, and arbitrary non-negative angles
  - Quality: `default`
  - Format: `jpg`, `png`
- Standalone server mode via `uvicorn sanf.main:create_app --factory`.
- `IIIF_SOURCE_ROOT` environment variable for configuring the image root directory.
