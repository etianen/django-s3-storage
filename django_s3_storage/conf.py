from __future__ import unicode_literals

"""
Settings used by django-s3-storage.
"""

from django.conf import settings


class LazySetting(object):

    """
    A proxy to a named Django setting.
    """

    def __init__(self, name, default=""):
        self.name = name
        self.default = default

    def __get__(self, obj, cls):
        if obj is None:
            return self
        return getattr(obj._settings, self.name, self.default)


class LazySettings(object):

    """
    A proxy to s3-specific django settings.

    Settings are resolved at runtime, allowing tests
    to change settings at runtime.
    """

    def __init__(self, settings):
        self._settings = settings

    AWS_REGION = LazySetting(
        name = "AWS_REGION",
        default = "us-east-1",
    )

    AWS_ACCESS_KEY_ID = LazySetting(
        name = "AWS_ACCESS_KEY_ID",
    )

    AWS_SECRET_ACCESS_KEY = LazySetting(
        name = "AWS_SECRET_ACCESS_KEY",
    )

    # Media storage config.

    AWS_S3_BUCKET_NAME = LazySetting(
        name = "AWS_S3_BUCKET_NAME",
    )

    AWS_S3_KEY_PREFIX = LazySetting(
        name = "AWS_S3_KEY_PREFIX",
    )

    AWS_S3_BUCKET_AUTH = LazySetting(
        name = "AWS_S3_BUCKET_AUTH",
        default = True,
    )

    AWS_S3_MAX_AGE_SECONDS = LazySetting(
        name = "AWS_S3_MAX_AGE_SECONDS",
        default = 60 * 60,  # 1 hours.
    )

    # Static storage config.

    AWS_S3_BUCKET_NAME_STATIC = LazySetting(
        name = "AWS_S3_BUCKET_NAME_STATIC",
    )

    AWS_S3_KEY_PREFIX_STATIC = LazySetting(
        name = "AWS_S3_KEY_PREFIX_STATIC",
    )

    AWS_S3_BUCKET_AUTH_STATIC = LazySetting(
        name = "AWS_S3_BUCKET_AUTH_STATIC",
        default = False,
    )

    AWS_S3_MAX_AGE_SECONDS_STATIC = LazySetting(
        name = "AWS_S3_MAX_AGE_SECONDS_STATIC",
        default = 60 * 60 * 24 * 365,  # 1 year.
    )


settings = LazySettings(settings)
