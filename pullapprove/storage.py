import json
from typing import Any, Optional

from pullapprove.logger import logger
from pullapprove.settings import settings


class Storage:
    def store_data(self, key: str, data: Any) -> Optional[str]:
        expiration_days = int(settings.get("REPORT_EXPIRATION_DAYS", "7"))

        if settings.get("AWS_S3_BUCKET", False):
            import boto3

            # use an iam user for longer expiration on signed url
            boto_session = boto3.Session(
                aws_access_key_id=settings.get("AWS_IAM_USER_ACCESS_KEY_ID"),
                aws_secret_access_key=settings.get("AWS_IAM_USER_SECRET_ACCESS_KEY"),
            )
            s3 = boto_session.resource("s3")
            obj = s3.Object(settings.get("AWS_S3_BUCKET"), key)

            if expiration_days > 0:
                obj.put(
                    Body=json.dumps(data).encode("utf-8"),
                    ContentType="application/json",
                )
                logger.debug(f"storage.uploaded where=s3 key={key}")

                url = obj.meta.client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": obj.bucket_name, "Key": obj.key},
                    ExpiresIn=(expiration_days * 24 * 60 * 60),
                )
                logger.debug(f"storage.generated_url where=s3 url={url}")

                return url

            else:
                # Public objects
                obj.put(
                    Body=json.dumps(data).encode("utf-8"),
                    ContentType="application/json",
                    ACL="public-read",
                )
                logger.debug(f"storage.uploaded where=s3 key={key}")

                # Hacky way to get public object url easily - signed url and then remove all params
                url = obj.meta.client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": obj.bucket_name, "Key": obj.key},
                )
                url = url.split("?")[0]
                logger.debug(f"storage.generated_url where=s3 url={url}")

                return url

        # if neither is configured, don't return a url and just silently pass for now
        return None
