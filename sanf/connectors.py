from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class ImageSourceConnector(Protocol):
    """Storage connector contract for IIIF source image retrieval.

    Requirements for production connectors:
    - `fetch_image_bytes` must return full original image bytes for a stable identifier.
    - Raise `ImageNotFoundError` when the identifier does not exist.
    - Raise `ConnectorError` for transient/backend failures.
    - Identifier input is already URL-decoded by the service layer.
    """

    def fetch_image_bytes(self, identifier: str) -> bytes:
        ...


class ConnectorError(RuntimeError):
    """Generic connector failure."""


class ImageNotFoundError(ConnectorError):
    """Identifier was not found in backing storage."""


@dataclass(slots=True)
class LocalFileConnector:
    """Simple filesystem connector for local/dev usage.

    The identifier maps directly to a relative file path under `root`.
    """

    root: Path

    _EXTENSIONS = (".jpg", ".jpeg", ".png", ".tif", ".tiff")

    def fetch_image_bytes(self, identifier: str) -> bytes:
        root_path = self.root.resolve()
        base_path = (self.root / identifier).resolve()

        if not str(base_path).startswith(str(root_path)):
            raise ImageNotFoundError("invalid identifier path")

        image_path = next(
            (p for ext in self._EXTENSIONS if (p := base_path.with_suffix(ext)).is_file()),
            None,
        )
        if image_path is None:
            raise ImageNotFoundError(f"identifier not found: {identifier}")

        try:
            return image_path.read_bytes()
        except OSError as exc:
            raise ConnectorError("failed to read source image") from exc
