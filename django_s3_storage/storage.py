from __future__ import unicode_literals
import gzip
import mimetypes
import os
import posixpath
import shutil
from io import TextIOBase
from contextlib import closing
from functools import wraps
from tempfile import SpooledTemporaryFile
import boto3
from botocore.exceptions import ClientError
from botocore.client import Config
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import Storage
from django.core.files.base import File
from django.core.signals import setting_changed
from django.contrib.staticfiles.storage import ManifestFilesMixin
from django.utils.six.moves.urllib.parse import urlsplit, urlunsplit, urljoin
from django.utils.deconstruct import deconstructible
from django.utils.encoding import force_bytes, filepath_to_uri, force_text, force_str
from django.utils.timezone import make_naive, utc


def _wrap_errors(func):
    @wraps(func)
    def _do_wrap_errors(self, name, *args, **kwargs):
        try:
            return func(self, name, *args, **kwargs)
        except ClientError as ex:
            raise OSError("S3Storage error at {!r}: {}".format(name, force_text(ex)))
    return _do_wrap_errors


def _callable_setting(value, name):
    return value(name) if callable(value) else value


def _temporary_file():
    return SpooledTemporaryFile(max_size=1024*1024*10)  # 10 MB.


class S3File(File):

    """
    A file returned from Amazon S3.
    """

    def __init__(self, file, name, storage):
        super(S3File, self).__init__(file, name)
        self._storage = storage

    def open(self, mode="rb"):
        if self.closed:
            self.file = self._storage.open(self.name, mode).file
        return super(S3File, self).open(mode)


@deconstructible
class S3Storage(Storage):

    """
    An implementation of Django file storage over S3.
    """

    default_auth_settings = {
        "AWS_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "",
        "AWS_SECRET_ACCESS_KEY": "",
    }

    default_s3_settings = {
        "AWS_S3_BUCKET_NAME": "",
        "AWS_S3_ADDRESSING_STYLE": "auto",
        "AWS_S3_ENDPOINT_URL": "",
        "AWS_S3_KEY_PREFIX": "",
        "AWS_S3_BUCKET_AUTH": True,
        "AWS_S3_MAX_AGE_SECONDS": 60 * 60,  # 1 hours.
        "AWS_S3_PUBLIC_URL": "",
        "AWS_S3_REDUCED_REDUNDANCY": False,
        "AWS_S3_CONTENT_DISPOSITION": "",
        "AWS_S3_CONTENT_LANGUAGE": "",
        "AWS_S3_METADATA": {},
        "AWS_S3_ENCRYPT_KEY": False,
        "AWS_S3_GZIP": True,
        "AWS_S3_SIGNATURE_VERSION": "s3v4",
    }

    s3_settings_suffix = ""

    def _setup(self):
        self.settings = type(force_str("Settings"), (), {})()
        # Configure own settings.
        for setting_key, setting_default_value in self.default_auth_settings.items():
            setattr(
                self.settings,
                setting_key,
                self._kwargs.get(
                    setting_key.lower(),
                    getattr(settings, setting_key, setting_default_value),
                ),
            )
        for setting_key, setting_default_value in self.default_s3_settings.items():
            setattr(
                self.settings,
                setting_key,
                self._kwargs.get(
                    setting_key.lower(),
                    getattr(settings, setting_key + self.s3_settings_suffix, setting_default_value),
                ),
            )
        # Validate settings.
        if self.settings.AWS_S3_PUBLIC_URL and self.settings.AWS_S3_BUCKET_AUTH:
            raise ImproperlyConfigured("Cannot use AWS_S3_BUCKET_AUTH with AWS_S3_PUBLIC_URL.")
        # Connect to S3.
        connection_kwargs = {
            "region_name": self.settings.AWS_REGION,
        }
        if self.settings.AWS_ACCESS_KEY_ID:
            connection_kwargs["aws_access_key_id"] = self.settings.AWS_ACCESS_KEY_ID
        if self.settings.AWS_SECRET_ACCESS_KEY:
            connection_kwargs["aws_secret_access_key"] = self.settings.AWS_SECRET_ACCESS_KEY
        if self.settings.AWS_S3_ENDPOINT_URL:
            connection_kwargs["endpoint_url"] = self.settings.AWS_S3_ENDPOINT_URL
        self.s3_connection = boto3.client("s3", config=Config(
            s3={"addressing_style": self.settings.AWS_S3_ADDRESSING_STYLE},
            signature_version=self.settings.AWS_S3_SIGNATURE_VERSION,
        ), **connection_kwargs)

    def _setting_changed_received(self, setting, **kwargs):
        if setting.startswith("AWS_"):
            # HACK: No supported way to close the HTTP session from boto3... :S
            self.s3_connection._endpoint.http_session.close()
            self._setup()

    def __init__(self, **kwargs):
        # Check for unknown kwargs.
        for kwarg_key in kwargs.keys():
            if (
                kwarg_key.upper() not in self.default_auth_settings and
                kwarg_key.upper() not in self.default_s3_settings
            ):
                raise ImproperlyConfigured("Unknown S3Storage parameter: {}".format(kwarg_key))
        # Set up the storage.
        self._kwargs = kwargs
        self._setup()
        # Re-initialize the storage if an AWS setting changes.
        setting_changed.connect(self._setting_changed_received)
        # All done!
        super(S3Storage, self).__init__()

    # Helpers.

    def _get_key_name(self, name):
        if name.startswith("/"):
            name = name[1:]
        return posixpath.normpath(posixpath.join(self.settings.AWS_S3_KEY_PREFIX, name.replace(os.sep, "/")))

    def _object_params(self, name):
        params = {
            "Bucket": self.settings.AWS_S3_BUCKET_NAME,
            "Key": self._get_key_name(name),
        }
        return params

    def _object_put_params(self, name):
        # Set basic params.
        params = {
            "ACL": "private" if self.settings.AWS_S3_BUCKET_AUTH else "public-read",
            "CacheControl": "{privacy},max-age={max_age}".format(
                privacy="private" if self.settings.AWS_S3_BUCKET_AUTH else "public",
                max_age=self.settings.AWS_S3_MAX_AGE_SECONDS,
            ),
            "Metadata": {
                key: _callable_setting(value, name)
                for key, value
                in self.settings.AWS_S3_METADATA.items()
            },
            "StorageClass": "REDUCED_REDUNDANCY" if self.settings.AWS_S3_REDUCED_REDUNDANCY else "STANDARD",
        }
        params.update(self._object_params(name))
        # Set content disposition.
        content_disposition = _callable_setting(self.settings.AWS_S3_CONTENT_DISPOSITION, name)
        if content_disposition:
            params["ContentDisposition"] = content_disposition
        # Set content langauge.
        content_langauge = _callable_setting(self.settings.AWS_S3_CONTENT_LANGUAGE, name)
        if content_langauge:
            params["ContentLanguage"] = content_langauge
        # Set server-side encryption.
        if self.settings.AWS_S3_ENCRYPT_KEY:
            params["ServerSideEncryption"] = "AES256"
        # All done!
        return params

    @_wrap_errors
    def _open(self, name, mode="rb"):
        if mode != "rb":
            raise ValueError("S3 files can only be opened in read-only mode")
        # Load the key into a temporary file. It would be nice to stream the
        # content, but S3 doesn't support seeking, which is sometimes needed.
        obj = self.s3_connection.get_object(**self._object_params(name))
        content = _temporary_file()
        shutil.copyfileobj(obj["Body"], content)
        content.seek(0)
        # Un-gzip if required.
        if obj.get("ContentEncoding") == "gzip":
            content = gzip.GzipFile(name, "rb", fileobj=content)
        # All done!
        return S3File(content, name, self)

    @_wrap_errors
    def _save(self, name, content):
        put_params = self._object_put_params(name)
        temp_files = []
        # The Django file storage API always rewinds the file before saving,
        # therefor so should we.
        content.seek(0)
        # Convert content to bytes.
        if isinstance(content.file, TextIOBase):
            temp_file = _temporary_file()
            temp_files.append(temp_file)
            for chunk in content.chunks():
                temp_file.write(force_bytes(chunk))
            temp_file.seek(0)
            content = temp_file
        # Calculate the content type.
        content_type, _ = mimetypes.guess_type(name, strict=False)
        content_type = content_type or "application/octet-stream"
        put_params["ContentType"] = content_type
        # Calculate the content encoding.
        if self.settings.AWS_S3_GZIP:
            # Check if the content type is compressible.
            content_type_family, content_type_subtype = content_type.lower().split("/")
            content_type_subtype = content_type_subtype.split("+")[-1]
            if content_type_family == "text" or content_type_subtype in ("xml", "json", "html", "javascript"):
                # Compress the content.
                temp_file = _temporary_file()
                temp_files.append(temp_file)
                with closing(gzip.GzipFile(name, "wb", 9, temp_file)) as gzip_file:
                    shutil.copyfileobj(content, gzip_file)
                # Only use the compressed version if the zipped version is actually smaller!
                if temp_file.tell() < content.tell():
                    temp_file.seek(0)
                    content = temp_file
                    put_params["ContentEncoding"] = "gzip"
                else:
                    content.seek(0)
        # Save the file.
        self.s3_connection.put_object(Body=content, **put_params)
        # Close all temp files.
        for temp_file in temp_files:
            temp_file.close()
        # All done!
        return name

    # Subsiduary storage methods.

    @_wrap_errors
    def meta(self, name):
        """Returns a dictionary of metadata associated with the key."""
        return self.s3_connection.head_object(**self._object_params(name))

    @_wrap_errors
    def delete(self, name):
        self.s3_connection.delete_object(**self._object_params(name))

    def directory_exists(self, name):
        # We also need to check for directory existence, so we'll list matching
        # keys and return success if any match.
        results = self.s3_connection.list_objects_v2(
            Bucket=self.settings.AWS_S3_BUCKET_NAME,
            MaxKeys=1,
            Prefix=self._get_key_name(name),
        )
        return bool(results["KeyCount"])

    def exists(self, name):
        """
        Find out of the file exists already in s3.

        We check to see if this is a directory, if it is, we then use
        directory_exists() to find out if it exists in s3. We need to do things
        differently when it is a directory since s3 doesn't treat them the
        same way as files.

        If not a directory, then we will make a HEAD call and see if the
        file exists without throwing an error.
        """
        if name and name.endswith("/"):
            # it is a directory
            return self.directory_exists(name)
        # it is not a directory, check if the object exists by using the
        # head object call, which makes a HEAD http request. If the call
        # doesn't throw an error, then we know it exists.
        try:
            self.s3_connection.head_object(
                Bucket=self.settings.AWS_S3_BUCKET_NAME,
                Key=self._get_key_name(name))
            # we got an object with no exception, the file exists.
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                # file doesn't exist
                return False
            else:
                # it wasn't an error we were expecting, raise it up
                raise e

    def listdir(self, path):
        path = self._get_key_name(path)
        path = "" if path == "." else path + "/"
        # Look through the paths, parsing out directories and paths.
        files = []
        dirs = []
        paginator = self.s3_connection.get_paginator("list_objects_v2")
        pages = paginator.paginate(
            Bucket=self.settings.AWS_S3_BUCKET_NAME,
            Delimiter="/",
            Prefix=path,
        )
        for page in pages:
            for entry in page.get("Contents", ()):
                files.append(posixpath.relpath(entry["Key"], path))
            for entry in page.get("CommonPrefixes", ()):
                dirs.append(posixpath.relpath(entry["Prefix"], path))
        # All done!
        return dirs, files

    def size(self, name):
        return self.meta(name)["ContentLength"]

    def url(self, name):
        # Use a public URL, if specified.
        if self.settings.AWS_S3_PUBLIC_URL:
            return urljoin(self.settings.AWS_S3_PUBLIC_URL, filepath_to_uri(name))
        # Otherwise, generate the URL.
        url = self.s3_connection.generate_presigned_url(
            ClientMethod="get_object",
            Params=self._object_params(name),
            ExpiresIn=self.settings.AWS_S3_MAX_AGE_SECONDS,
        )
        # Strip off the query params if we're not interested in bucket auth.
        if not self.settings.AWS_S3_BUCKET_AUTH:
            url = urlunsplit(urlsplit(url)[:3] + ("", "",))
        # All done!
        return url

    def modified_time(self, name):
        return make_naive(self.meta(name)["LastModified"], utc)

    created_time = accessed_time = modified_time

    def get_modified_time(self, name):
        timestamp = self.meta(name)["LastModified"]
        return timestamp if settings.USE_TZ else make_naive(timestamp)

    get_created_time = get_accessed_time = get_modified_time

    def sync_meta_iter(self):
        paginator = self.s3_connection.get_paginator("list_objects_v2")
        pages = paginator.paginate(
            Bucket=self.settings.AWS_S3_BUCKET_NAME,
            Prefix=self.settings.AWS_S3_KEY_PREFIX,
        )
        for page in pages:
            for entry in page.get("Contents", ()):
                name = posixpath.relpath(entry["Key"], self.settings.AWS_S3_KEY_PREFIX)
                try:
                    obj = self.meta(name)
                except OSError:
                    # This may be caused by a race condition, with the entry being deleted before it was accessed.
                    # Alternatively, the key may be something that, when normalized, has a different path, which will
                    # mean that the key's meta cannot be accessed.
                    continue
                put_params = self._object_put_params(name)
                # Set content encoding.
                content_encoding = obj.get("ContentEncoding")
                if content_encoding:
                    put_params["ContentEncoding"] = content_encoding
                # Update the metadata.
                self.s3_connection.copy_object(
                    ContentType=obj["ContentType"],
                    CopySource={
                        "Bucket": self.settings.AWS_S3_BUCKET_NAME,
                        "Key": self._get_key_name(name),
                    },
                    MetadataDirective="REPLACE",
                    **put_params
                )
                yield name

    def sync_meta(self):
        for path in self.sync_meta_iter():
            pass


class StaticS3Storage(S3Storage):

    """
    An S3 storage for storing static files.
    """

    default_s3_settings = S3Storage.default_s3_settings.copy()
    default_s3_settings.update({
        "AWS_S3_BUCKET_AUTH": False,
        "AWS_S3_MAX_AGE_SECONDS": 60 * 60 * 24 * 365,  # 1 year.
    })

    s3_settings_suffix = "_STATIC"


class ManifestStaticS3Storage(ManifestFilesMixin, StaticS3Storage):

    pass
