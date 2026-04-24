"""
Custom connector backed by Google Cloud Storage.

Install the extra dependency before running:
    pip install google-cloud-storage

Authentication uses Application Default Credentials (ADC). Set up with:
    gcloud auth application-default login

Or point to a service account key file:
    GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json uvicorn examples.06_gcs_connector:app --reload

Run with:
    uvicorn examples.06_gcs_connector:app --reload
"""

from dataclasses import dataclass, field

from google.api_core.exceptions import GoogleAPICallError, NotFound
from google.cloud import storage

from sanf import (
    ConnectorError,
    IIIFServerSettings,
    ImageNotFoundError,
    create_app,
)


@dataclass
class GCSConnector:
    """Fetch source images from a Google Cloud Storage bucket.

    The IIIF identifier maps directly to a GCS object name (optionally
    prefixed), so an image stored at ``gs://my-bucket/source/page1.tif``
    is addressed by the identifier ``page1`` when ``prefix="source/"``.
    """

    bucket: str
    prefix: str = ""
    _client: storage.Client = field(init=False, repr=False)
    _bucket_ref: storage.Bucket = field(init=False, repr=False)

    _EXTENSIONS = (".jpg", ".jpeg", ".png", ".tif", ".tiff")

    def __post_init__(self) -> None:
        self._client = storage.Client()
        self._bucket_ref = self._client.bucket(self.bucket)

    def fetch_image_bytes(self, identifier: str) -> bytes:
        name = f"{self.prefix}{identifier}"
        for ext in self._EXTENSIONS:
            blob = self._bucket_ref.blob(name + ext)
            try:
                return blob.download_as_bytes()
            except NotFound:
                continue
            except GoogleAPICallError as exc:
                raise ConnectorError(f"GCS error: {exc}") from exc

        raise ImageNotFoundError(f"identifier not found in GCS: {identifier}")


settings = IIIFServerSettings(
    connector=GCSConnector(bucket="my-iiif-images", prefix="source/"),
    jpeg_quality=90,
)

app = create_app(settings)
