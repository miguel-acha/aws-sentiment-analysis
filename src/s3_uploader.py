"""
s3_uploader.py
--------------
Sube el PNG del reporte a S3 y retorna la URL pública.
"""

import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone


def upload_report(
    png_bytes: bytes,
    playlist_id: str,
    bucket_name: str | None = None,
) -> dict:
    """
    Sube el PNG a S3.

    Args:
        png_bytes: Bytes del PNG generado
        playlist_id: ID de la playlist (usado como parte del key)
        bucket_name: Nombre del bucket S3 (default: variable de entorno S3_BUCKET_NAME)

    Returns:
        Dict con { url, key, bucket }
    """
    bucket = bucket_name or os.environ.get("S3_BUCKET_NAME", "spotify-sentiment-reports")
    region = os.environ.get("AWS_REGION", "us-east-1")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    key = f"reports/{playlist_id}_{timestamp}.png"

    s3 = boto3.client("s3", region_name=region)

    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=png_bytes,
            ContentType="image/png",
        )

        url = f"https://{bucket}.s3.amazonaws.com/{key}"
        print(f"[s3_uploader] PNG subido: {url}")
        return {"url": url, "key": key, "bucket": bucket}

    except ClientError as e:
        print(f"[s3_uploader] Error subiendo a S3: {e}")
        raise


def ensure_bucket_exists(bucket_name: str, region: str = "us-east-1") -> None:
    """Crea el bucket si no existe (útil para setup inicial)."""
    s3 = boto3.client("s3", region_name=region)
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"[s3_uploader] Bucket '{bucket_name}' ya existe.")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "404":
            print(f"[s3_uploader] Creando bucket '{bucket_name}'...")
            if region == "us-east-1":
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": region},
                )
            print(f"[s3_uploader] Bucket '{bucket_name}' creado.")
        else:
            raise
