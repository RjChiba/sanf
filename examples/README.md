# sanf — Usage Examples

Each example below is a self-contained Python file you can run directly.
All examples assume you have installed the package:

```bash
pip install sanf
```

---

## 1. Standalone server

**File:** [01_standalone_server.py](01_standalone_server.py)

The simplest possible setup: point `LocalFileConnector` at a directory that
contains your source images and call `create_app`. The resulting `FastAPI`
instance has CORS (`*`) enabled automatically and exposes all IIIF endpoints
under `/iiif`.

```python
from pathlib import Path
from sanf import IIIFServerSettings, LocalFileConnector, create_app

settings = IIIFServerSettings(
    connector=LocalFileConnector(root=Path("./images")),
)

app = create_app(settings)
```

Run it:

```bash
uvicorn examples.01_standalone_server:app --reload
```

Once running, the endpoints are:

| URL | Description |
|---|---|
| `GET /iiif/{id}` | 303 redirect to `info.json` |
| `GET /iiif/{id}/info.json` | Image metadata (dimensions, profile, …) |
| `GET /iiif/{id}/full/max/0/default.jpg` | Full image at full resolution |
| `GET /iiif/{id}/pct:10,10,80,80/!800,600/0/default.png` | Cropped & resized PNG |

---

## 2. Embedding the IIIF router into an existing FastAPI application

**File:** [02_embed_in_fastapi.py](02_embed_in_fastapi.py)

Use `create_iiif_router` when you already have a `FastAPI` application and
want to add IIIF support to it. The router does **not** add CORS middleware,
so the host application controls that policy.

```python
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
```

The IIIF endpoints coexist with any other routes you add to `app`. The `prefix`
argument lets you mount them at any path (e.g. `/images/iiif`).

---

## 3. Custom connector — AWS S3

**File:** [03_s3_connector.py](03_s3_connector.py)

`sanf` is not limited to the local filesystem. Any class that implements
`fetch_image_bytes(identifier: str) -> bytes` can act as a connector. The
example below fetches source images from an S3 bucket, trying common image
extensions in order.

```python
import boto3
from botocore.exceptions import ClientError
from dataclasses import dataclass, field
from sanf import ConnectorError, IIIFServerSettings, ImageNotFoundError, create_app

@dataclass
class S3Connector:
    bucket: str
    prefix: str = ""
    _client: object = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = boto3.client("s3")

    def fetch_image_bytes(self, identifier: str) -> bytes:
        key = f"{self.prefix}{identifier}"
        for ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff"):
            try:
                response = self._client.get_object(Bucket=self.bucket, Key=key + ext)
                return response["Body"].read()
            except ClientError as exc:
                code = exc.response["Error"]["Code"]
                if code in ("NoSuchKey", "404"):
                    continue
                raise ConnectorError(f"S3 error: {exc}") from exc
        raise ImageNotFoundError(f"identifier not found in S3: {identifier}")

settings = IIIFServerSettings(
    connector=S3Connector(bucket="my-iiif-images", prefix="source/"),
)
app = create_app(settings)
```

The connector raises `ImageNotFoundError` when no matching key is found, which
the IIIF router automatically converts to an HTTP 404 response. Any other
`ClientError` becomes a `ConnectorError`, which maps to HTTP 502.

Install `boto3` before running:

```bash
pip install boto3
AWS_DEFAULT_REGION=us-east-1 uvicorn examples.03_s3_connector:app --reload
```

---

## 4. Custom connector — Google Cloud Storage

**File:** [06_gcs_connector.py](06_gcs_connector.py)

The GCS connector follows the same pattern as the S3 one: iterate over known
extensions, map `NotFound` to `ImageNotFoundError`, and re-raise any other API
error as `ConnectorError`.

```python
from dataclasses import dataclass, field
from google.api_core.exceptions import GoogleAPICallError, NotFound
from google.cloud import storage
from sanf import ConnectorError, IIIFServerSettings, ImageNotFoundError, create_app

@dataclass
class GCSConnector:
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
)
app = create_app(settings)
```

Authentication uses [Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc).
Set them up with the `gcloud` CLI, or point to a service account key file:

```bash
pip install google-cloud-storage

# Option A — developer login
gcloud auth application-default login

# Option B — service account key
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json \
    uvicorn examples.06_gcs_connector:app --reload
```

The `_client` and `_bucket_ref` are initialised once in `__post_init__` and
reused across requests, so the GCS HTTP connection pool is shared for the
lifetime of the process.
