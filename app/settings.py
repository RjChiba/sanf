from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from app.connectors import ImageSourceConnector


@dataclass
class IIIFServerSettings:
    connector: ImageSourceConnector
    cors_origins: Sequence[str] = field(default_factory=lambda: ["*"])
    jpeg_quality: int = 85
    max_width: int | None = None
    max_height: int | None = None
