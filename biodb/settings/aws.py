from .prd import *  # noqa F403
import os


# Media files.
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": os.getenv("AWS_STORAGE_BUCKET_NAME"),
            "region_name": os.getenv("AWS_S3_REGION_NAME"),
            "use_ssl": True,
            "url_protocol": "https",
            "file_overwrite": False,  # Set this to False to have extra characters appended.
            "default_acl": "private",  # https://docs.aws.amazon.com/AmazonS3/latest/userguide/acl-overview.html#canned-acl
            "querystring_auth": True,  # Query parameter authentication from generated URLs.
            "querystring_expire": os.getenv(
                "AWS_QUERYSTRING_AUTH"
            ),  # The number of seconds that a generated URL is valid for.
            "object_parameters": {"Cache-Control": "no-cache"},
        },
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

if not HOST_DOMAIN:  # noqa: F405
    raise OSError(
        "A 'HOST_DOMAIN' env var must be set! " "See https://docs.djangoproject.com/en/5.0/ref/settings/#allowed-hosts"
    )
ALLOWED_HOSTS = [f".{HOST_DOMAIN}"]  # noqa: F405
