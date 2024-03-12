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
            "url_protocol": "https"
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    }
}

HOST_DOMAIN = os.getenv("HOST_DOMAIN")
if not HOST_DOMAIN:
    raise OSError("A 'HOST_DOMAIN' env var must be set! "
                  "See https://docs.djangoproject.com/en/5.0/ref/settings/#allowed-hosts")
ALLOWED_HOSTS = [f".{HOST_DOMAIN}"]
