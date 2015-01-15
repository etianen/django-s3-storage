from __future__ import unicode_literals

import datetime, mimetypes, gzip
from io import TextIOBase
from email.utils import parsedate_tz
from contextlib import closing
from tempfile import SpooledTemporaryFile

from boto import s3
from boto.s3.connection import S3ResponseError

from django.conf import settings
from django.core.files.storage import Storage
from django.core.files.base import File
from django.contrib.staticfiles.storage import ManifestFilesMixin
from django.utils.deconstruct import deconstructible
from django.utils import timezone
from django.utils.encoding import force_bytes

from django_s3_storage.conf import settings


CONTENT_ENCODING_GZIP = "gzip"


@deconstructible
class S3Storage(Storage):

    """
    An implementation of Django file storage over S3.

    It would be nice to use django-storages for this, but it doesn't support
    Python 3, which is kinda lame.
    """

    def __init__(self, aws_region=None, aws_access_key_id=None, aws_secret_access_key=None, aws_s3_bucket_name=None, aws_s3_bucket_auth=True):
        self.aws_region = aws_region or settings.AWS_REGION
        self.aws_access_key_id = aws_access_key_id or settings.AWS_ACCESS_KEY_ID
        self.aws_secret_access_key = aws_secret_access_key or settings.AWS_SECRET_ACCESS_KEY
        self.aws_s3_bucket_name = aws_s3_bucket_name or settings.AWS_S3_BUCKET_NAME
        self.aws_s3_bucket_auth = aws_s3_bucket_auth
        # Connect to S3.
        self.s3_connection = s3.connect_to_region(
            self.aws_region,
            aws_access_key_id = self.aws_access_key_id,
            aws_secret_access_key = self.aws_secret_access_key,
            calling_format = "boto.s3.connection.OrdinaryCallingFormat",
        )
        self.bucket = self.s3_connection.get_bucket(self.aws_s3_bucket_name)
        # All done!
        super(S3Storage, self).__init__()

    # Helpers.

    def _get_content_type(self, name):
        """Calculates the content type of the file from the name."""
        content_type, encoding = mimetypes.guess_type(name, strict=False)
        content_type = content_type or "application/octet-stream"
        return content_type

    def _get_max_age(self):
        """
        Calculates an appropriate expiry time (in seconds) files.

        Files in non-authenticated storage get a very long expiry time to
        optimize caching.
        """
        if self.aws_s3_bucket_auth:
            delta = datetime.timedelta(hours=1)
        else:
            delta = datetime.timedelta(days=365)
        return int(delta.total_seconds())

    def _get_cache_control(self):
        """
        Calculates an appropriate cache-control header for files.

        Files in non-authenticated storage get a very long expiry time to
        optimize caching, as well as public caching support.
        """
        if self.aws_s3_bucket_auth:
            privacy = "private"
        else:
            privacy = "public"
        return force_bytes("{privacy}, max-age={max_age}".format(
            privacy = privacy,
            max_age = self._get_max_age(),
        ))  # Have to use bytes else the space will be percent-encoded. Odd, eh?

    def _get_content_encoding(self, content_type):
        """
        Generates an appropriate content-encoding header for the given
        content type.

        Content types that are known to be compressible (i.e. text-based)
        types, are recommended for gzip.
        """
        family, subtype = content_type.lower().split("/")
        subtype = subtype.split("+")[-1]
        if family == "text" or subtype in ("xml", "json", "html"):
            return CONTENT_ENCODING_GZIP
        return None

    def _temporary_file(self):
        """
        Creates a temporary file.

        We need a lot of these, so they are tweaked for efficiency.
        """
        return SpooledTemporaryFile(max_size=1024*1024*10)  # 10 MB.

    def _convert_content_to_bytes(self, name, content):
        """
        Forces the given text-mode file into a bytes-mode file.
        """
        temp_file = self._temporary_file()
        temp_file.write(force_bytes(content.read()))
        temp_file.seek(0)
        return File(temp_file, name)

    def _conditional_compress_file(self, name, content):
        """
        Attempts to compress the given file.

        If the file is larger when compressed, returns the original
        file.

        Returns a tuple of (content_encoding, content).
        """
        content_bytes = content.read()
        # Ideally, we would do some sort of incremental compression here,
        # but boto doesn't support uploading a key from an iterator.
        temp_file = self._temporary_file()
        with closing(gzip.GzipFile(name, "wb", 9, temp_file)) as zipfile:
            zipfile.write(content_bytes)
        # Check if the zipped version is actually smaller!
        if temp_file.tell() < len(content_bytes):
            temp_file.seek(0)
            content = File(temp_file, name)
            return CONTENT_ENCODING_GZIP, content
        else:
            # Haha! Gzip made it bigger.
            content.seek(0)
            return None, content

    def _process_file_for_upload(self, name, content):
        """
        For a given filename and file, returns a tuple of
        (content_type, content_encoding, content). The content
        may or may not be the same file as the original.
        """
        # The Django file storage API always rewinds the file before saving,
        # therefor so should we.
        content.seek(0)
        # Calculate the content type.
        content_type = self._get_content_type(name)
        # Convert files opened in text mode to binary mode.
        if isinstance(content.file, TextIOBase):
            content = self._convert_content_to_bytes(name, content)
        # Attempt content compression.
        content_encoding = self._get_content_encoding(content_type)
        if content_encoding == CONTENT_ENCODING_GZIP:
            content_encoding, content = self._conditional_compress_file(name, content)
        # Return the calculated headers and file.
        return content_type, content_encoding, content

    def _generate_url(self, name):
        """
        Generates a URL to the given file.

        Authenticated storage will return a signed URL. Non-authenticated
        storage will return an unsigned URL, which aids in browser caching.
        """
        return self.s3_connection.generate_url(
            method = "GET",
            bucket = self.aws_s3_bucket_name,
            key = name,
            expires_in = self._get_max_age(),
            query_auth = self.aws_s3_bucket_auth,
        )

    def _get_key(self, name, validate=False):
        return self.bucket.get_key(name, validate=validate)

    def _open(self, name, mode="rb"):
        if (mode != "rb"):
            raise ValueError("S3 files can only be opened in read-only mode")
        # Load the key into a temporary file. It would be nice to stream the
        # content, but S3 doesn't support seeking, which is sometimes needed.
        key = self._get_key(name)
        content = self._temporary_file()
        try:
            key.get_contents_to_file(content)
        except S3ResponseError:
            raise IOError("File {name} does not exist".format(
                name = name,
            ))
        content.seek(0)
        # Un-gzip if required.
        if key.content_encoding == CONTENT_ENCODING_GZIP:
            content = gzip.GzipFile(name, "rb", fileobj=content)
        # All done!
        return File(content, name)

    def _save(self, name, content):
        # Calculate the file headers and compression.
        content_type, content_encoding, content = self._process_file_for_upload(name, content)
        # Generate file headers.
        headers = {
            "Content-Type": content_type,
            "Cache-Control": self._get_cache_control(),
        }
        # Try to compress the file.
        if content_encoding is not None:
            headers["Content-Encoding"] = content_encoding
        # Save the file.
        self._get_key(name).set_contents_from_file(
            content,
            policy = "private" if self.aws_s3_bucket_auth else "public-read",
            headers = headers,
        )
        # Return the name that was saved.
        return name

    # Subsiduary storage methods.

    def delete(self, name):
        """
        Deletes the specified file from the storage system.
        """
        self._get_key(name).delete()

    def exists(self, name):
        """
        Returns True if a file referenced by the given name already exists in the
        storage system, or False if the name is available for a new file.
        """
        return self._get_key(name).exists()

    def listdir(self, path):
        """
        Lists the contents of the specified path, returning a 2-tuple of lists;
        the first item being directories, the second item being files.
        """
        # Normalize directory names.
        if path and not path.endswith("/"):
            path += "/"
        # Look through the paths, parsing out directories and paths.
        files = set()
        dirs = set()
        for key in self.bucket.list(prefix=path):
            key_path = key.name[len(path):]
            key_parts = key_path.split("/")
            if len(key_parts) == 1:
                files.add(key_path)
            else:
                dirs.add(key_parts[0])
        # All done!
        return list(dirs), list(files)

    def size(self, name):
        """
        Returns the total size, in bytes, of the file specified by name.
        """
        return self._get_key(name, validate=True).size

    def url(self, name):
        """
        Returns an absolute URL where the file's contents can be accessed
        directly by a Web browser.
        """
        return self._generate_url(name)

    def accessed_time(self, name):
        """
        Returns the last accessed time (as datetime object) of the file
        specified by name.

        Since this is not accessible via S3, the modified time is returned.
        """
        return self.modified_time(name)

    def created_time(self, name):
        """
        Returns the creation time (as datetime object) of the file
        specified by name.

        Since this is not accessible via S3, the modified time is returned.
        """
        return self.modified_time(name)

    def modified_time(self, name):
        """
        Returns the last modified time (as datetime object) of the file
        specified by name.
        """
        time_tuple = parsedate_tz(self._get_key(name, validate=True).last_modified)
        timestamp = datetime.datetime(*time_tuple[:6])
        offset = time_tuple[9]
        if offset is not None:
            # Convert to local time.
            timestamp = timezone.make_aware(timestamp, timezone.FixedOffset(offset))
            timestamp = timezone.make_naive(timestamp, timezone.utc)
        return timestamp


class StaticS3Storage(S3Storage):

    """
    An S3 storage for storing static files.

    Initializes the default bucket name frome the `AWS_S3_BUCKET_NAME_STATIC`
    setting, allowing different buckets to be used for static and uploaded
    files.

    By default, bucket auth is off, making file access more efficient and
    cacheable.
    """

    def __init__(self, **kwargs):
        kwargs["aws_s3_bucket_name"] = kwargs.get("aws_s3_bucket_name") or settings.AWS_S3_BUCKET_NAME_STATIC
        kwargs.setdefault("aws_s3_bucket_auth", False)
        super(StaticS3Storage, self).__init__(**kwargs)


class ManifestStaticS3Storage(ManifestFilesMixin, StaticS3Storage):

    pass
