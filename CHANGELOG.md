# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - Unreleased

### Changed
- Lower memory use and faster rendering in `render_image` ([#8](https://github.com/RjChiba/sanf/issues/8)).
  For a 5000×7000 JPEG, peak memory per tile or thumbnail request drops from ~270–430MB to
  ~5–140MB (`full/max` still needs the full-resolution image: ~420MB → ~270MB), and 12
  OpenSeadragon-style tiles at 6-way concurrency go from ~1.8GB / 5.2s to ~0.3GB / 0.95s.
  - The source is no longer converted to RGB when it is already `RGB` or `L`, which avoids a
    full-size copy.
  - JPEG sources are decoded with DCT scaling (1/2, 1/4, 1/8) when the requested output is small
    enough, so zoomed-out tiles and thumbnails no longer decode the full-resolution image.
  - Scaled output is resampled directly from the region (`resize(size, box=region)`) instead of
    `crop()` + `resize()`, which removes the intermediate copy and keeps regions aligned to
    sub-pixel accuracy after DCT scaling.
- Grayscale (`L`) sources are now encoded as grayscale JPEG/PNG instead of three-channel RGB.
- Scaled output pixel values differ slightly from 1.1.0, because JPEG DCT scaling replaces part of
  the Lanczos downscaling and resampling near region edges now uses the neighbouring source pixels.
  Output dimensions are unchanged, and requests without scaling (`size` equal to the region size)
  are pixel-identical.

## [1.1.0] - 2026-04-24

### Added
- `IIIFServerSettings.public_base_url` — optional setting to override the base URL used in `info.json`'s `id` field.
  When set (e.g. `https://proxy.example.com`), the scheme and host of the internal request URL are replaced with this value,
  allowing stable HTTPS URLs behind reverse proxies (Cloud Run, etc.) where TLS is terminated upstream.
  If unset, behavior is unchanged from 1.0.0.

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
