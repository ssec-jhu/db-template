# import os

from .prd import *  # noqa F403


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases


# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'admin',
#         "HOST": os.getenv("DB_ADMIN_HOST"),
#         "PORT": os.getenv("DB_ADMIN_PORT"),
#         "USER": os.getenv("DB_ADMIN_USER"),
#         "PASSWORD": os.getenv("DB_ADMIN_PASSWORD"),
#     },
#     "bsr": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": "bsr",
#         "HOST": os.getenv("DB_BSR_HOST"),
#         "PORT": os.getenv("DB_BSR_PORT"),
#         "USER": os.getenv("DB_BSR_USER"),
#         "PASSWORD": os.getenv("DB_BSR_PASSWORD"),
#     }
# }

ALLOWED_HOSTS = [".awsapprunner.com"]
