"""
Custom connector backed by AWS S3.

Install the extra dependency before running:
    pip install boto3

Run with:
    AWS_DEFAULT_REGION=us-east-1 uvicorn examples.03_s3_connector:app --reload
"""

from dataclasses import dataclass, field

import boto3
from botocore.exceptions import ClientError

from sanf import (
    ConnectorError,
    IIIFServerSettings,
    ImageNotFoundError,
    create_app,
)


@dataclass
class S3Connector:
    """Fetch source images from an S3 bucket.

    The IIIF identifier is used directly as the S3 object key, so an image
    stored at ``s3://my-bucket/manuscripts/page1.tif`` is addressed by the
    identifier ``manuscripts/page1``.
    """

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
    jpeg_quality=90,
)

app = create_app(settings)
