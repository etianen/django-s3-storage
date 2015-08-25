# coding=utf-8
from __future__ import unicode_literals

import posixpath, uuid, datetime, time
from unittest import skipUnless

import requests

from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils.encoding import force_bytes, force_text
from django.utils import timezone

from django_s3_storage.conf import settings
from django_s3_storage.storage import S3Storage, StaticS3Storage


@skipUnless(settings.AWS_REGION, "No settings.AWS_REGION supplied.")
@skipUnless(settings.AWS_ACCESS_KEY_ID, "No settings.AWS_ACCESS_KEY_ID supplied.")
@skipUnless(settings.AWS_SECRET_ACCESS_KEY, "No settings.AWS_SECRET_ACCESS_KEY supplied.")
@skipUnless(settings.AWS_S3_BUCKET_NAME, "No settings.AWS_S3_BUCKET_NAME supplied.")
@skipUnless(settings.AWS_S3_BUCKET_NAME_STATIC, "No settings.AWS_S3_BUCKET_NAME_STATIC supplied.")
class TestS3Storage(TestCase):

    # Lazy settings tests.

    def testLazySettingsInstanceLookup(self):
        self.assertTrue(settings.AWS_REGION)

    def testLazySettingsClassLookup(self):
        self.assertEqual(settings.__class__.AWS_REGION.name, "AWS_REGION")
        self.assertEqual(settings.__class__.AWS_REGION.default, "us-east-1")

    # Lifecycle.

    @classmethod
    def generateUploadBasename(cls, extension=None):
        return uuid.uuid4().hex + (extension or ".txt")

    @classmethod
    def generateUploadPath(cls, basename=None, extension=None):
        return posixpath.join(cls.upload_dir, basename or cls.generateUploadBasename(extension))

    @classmethod
    def saveTestFile(cls, upload_path=None, storage=None, file=None):
        (storage or cls.storage).save(upload_path or cls.upload_path, file or cls.file)
        time.sleep(0.2)  # Give it a chance to propagate over S3.

    @classmethod
    def setUpClass(cls):
        super(TestS3Storage, cls).setUpClass()
        cls.key_prefix = uuid.uuid4().hex
        cls.storage = S3Storage(aws_s3_key_prefix=cls.key_prefix)
        cls.insecure_storage = S3Storage(aws_s3_key_prefix=cls.key_prefix, aws_s3_bucket_auth=False, aws_s3_max_age_seconds=60*60*24*365)
        cls.key_prefix_static = uuid.uuid4().hex
        cls.static_storage = StaticS3Storage(aws_s3_key_prefix=cls.key_prefix_static)
        cls.upload_base = uuid.uuid4().hex
        cls.file_contents = force_bytes(uuid.uuid4().hex * 1000, "ascii")
        cls.file = ContentFile(cls.file_contents)
        cls.upload_dirname = uuid.uuid4().hex
        cls.upload_dir = posixpath.join(cls.upload_base, cls.upload_dirname)
        cls.upload_basename = cls.generateUploadBasename()
        cls.upload_path = cls.generateUploadPath(cls.upload_basename)
        cls.upload_time = datetime.datetime.now()
        # Save a file to the upload path.
        cls.saveTestFile()

    @classmethod
    def tearDownClass(cls):
        super(TestS3Storage, cls).tearDownClass()
        cls.storage.delete(cls.upload_path)

    # Assertions.

    def assertSimilarDatetime(self, a, b, resolution=datetime.timedelta(seconds=10)):
        """
        Assets that two datetimes are similar to each other.

        This allows testing of two generated timestamps that might differ by
        a few milliseconds due to network/disk latency, but should be roughly similar.

        The default resolution assumes that a 10-second window is similar
        enough, and can be tweaked with the `resolution` argument.
        """
        self.assertLess(abs(a - b), resolution)

    def assertCorrectTimestamp(self, timestamp):
        self.assertSimilarDatetime(timestamp, self.upload_time)
        self.assertTrue(timezone.is_naive(timestamp))

    def assertUrlAccessible(self, url, file_contents=None, content_type="text/plain", content_encoding="gzip"):
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("content-type"), content_type)
        self.assertEqual(response.headers.get("content-encoding"), content_encoding)
        self.assertEqual(response.content, file_contents or self.file_contents)
        return response

    def assertUrlInaccessible(self, url):
        response = requests.get(url)
        self.assertEqual(response.status_code, 403)

    # Tests.

    def testOpen(self):
        self.assertEqual(self.storage.open(self.upload_path).read(), self.file_contents)

    def testCannotOpenInWriteMode(self):
        with self.assertRaises(ValueError) as cm:
            self.storage.open(self.upload_path, "wb")
        self.assertEqual(force_text(cm.exception), "S3 files can only be opened in read-only mode")

    def testIOErrorRaisedOnOpenMissingFile(self):
        upload_path = self.generateUploadPath()
        with self.assertRaises(IOError) as cm:
            self.storage.open(upload_path)
        self.assertEqual(force_text(cm.exception), "File {name} does not exist".format(
            name = upload_path,
        ))

    def testSaveTextModeFile(self):
        upload_path = self.generateUploadPath()
        file_contents = "Fôö"  # Note the accents. This is a unicode string.
        self.storage.save(upload_path, ContentFile(file_contents, upload_path))
        try:
            stored_contents = self.storage.open(upload_path).read()
            self.assertEqual(stored_contents, force_bytes(file_contents))
        finally:
            self.storage.delete(upload_path)

    def testExists(self):
        self.assertTrue(self.storage.exists(self.upload_path))
        self.assertFalse(self.storage.exists(self.generateUploadPath()))

    def testDelete(self):
        # Make a new file to delete.
        upload_path = self.generateUploadPath()
        self.saveTestFile(upload_path)
        self.assertTrue(self.storage.exists(upload_path))
        # Delete the file.
        self.storage.delete(upload_path)
        self.assertFalse(self.storage.exists(upload_path))

    def testListdir(self):
        self.assertEqual(self.storage.listdir(self.upload_dir), ([], [self.upload_basename]))
        self.assertEqual(self.storage.listdir(self.upload_base), ([self.upload_dirname], []))

    def testSize(self):
        size = self.storage.size(self.upload_path)
        self.assertGreater(size, 100)  # It should take up some space!
        self.assertLess(size, len(self.file_contents))  # But less space than the original, due to gzipping.

    def testAccessedTime(self):
        self.assertCorrectTimestamp(self.storage.accessed_time(self.upload_path))

    def testCreatedTime(self):
        self.assertCorrectTimestamp(self.storage.created_time(self.upload_path))

    def testModifiedTime(self):
        self.assertCorrectTimestamp(self.storage.modified_time(self.upload_path))

    def testSecureUrlIsAccessible(self):
        # Generate a secure URL.
        url = self.storage.url(self.upload_path)
        # Ensure that the URL is signed.
        self.assertIn("?", url)
        # Ensure that the URL is accessible.
        response = self.assertUrlAccessible(url)
        self.assertEqual(response.headers["cache-control"], "private, max-age={max_age}".format(max_age=settings.AWS_S3_MAX_AGE_SECONDS))

    def testSecureUrlIsPrivate(self):
        # Generate an insecure URL.
        url = self.insecure_storage.url(self.upload_path)
        # Ensure that the URL is unsigned.
        self.assertNotIn("?", url)
        # Ensure that the unsigned URL is inaccessible.
        self.assertUrlInaccessible(url)

    def testInsecureUrlIsAccessible(self):
        # Make a new insecure file.
        upload_path = self.generateUploadPath()
        self.saveTestFile(upload_path, storage=self.insecure_storage)
        try:
            self.assertTrue(self.insecure_storage.exists(upload_path))
            # Generate an insecure URL.
            url = self.insecure_storage.url(upload_path)
            # Ensure that the URL is unsigned.
            self.assertNotIn("?", url)
            # Ensure that the URL is accessible.
            response = self.assertUrlAccessible(url)
            self.assertEqual(response.headers["cache-control"], "public, max-age=31536000")
        finally:
            # Clean up the test file.
            self.insecure_storage.delete(upload_path)

    def testNonGzippedFile(self):
        # Make a new non-gzipped file.
        upload_path = self.generateUploadPath(extension=".jpg")
        self.saveTestFile(upload_path)
        try:
            self.assertTrue(self.storage.exists(upload_path))
            # Generate a URL.
            url = self.storage.url(upload_path)
            # Ensure that the URL is accessible.
            self.assertUrlAccessible(url, content_type="image/jpeg", content_encoding=None)
        finally:
            # Clean up the test file.
            self.storage.delete(upload_path)

    def testSmallGzippedFile(self):
        # A tiny file gets bigger when gzipped.
        upload_path = self.generateUploadPath()
        file_contents = force_bytes(uuid.uuid4().hex, "ascii")
        self.saveTestFile(upload_path, file=ContentFile(file_contents))
        try:
            self.assertTrue(self.storage.exists(upload_path))
            # Generate a URL.
            url = self.storage.url(upload_path)
            # Ensure that the URL is accessible.
            self.assertUrlAccessible(url, file_contents=file_contents, content_encoding=None)
        finally:
            # Clean up the test file.
            self.storage.delete(upload_path)

    # Syncing meta information.

    def testSyncMetaPrivateToPublic(self):
        url = self.insecure_storage.url(self.upload_path)
        self.assertUrlInaccessible(url)
        # Sync the meta to insecure storage.
        self.insecure_storage.sync_meta()
        time.sleep(0.2)  # Give it a chance to propagate over S3.
        # URL is now accessible and well-cached.
        response = self.assertUrlAccessible(url)
        self.assertEqual(response.headers["cache-control"], "public, max-age=31536000")

    # Static storage tests.

    def testStaticS3StorageDefaultsToPublic(self):
        self.assertFalse(self.static_storage.aws_s3_bucket_auth)

    def testStaticS3StorageDefaultsToLongMaxAge(self):
        self.assertEqual(self.static_storage.aws_s3_max_age_seconds, 60*60*24*365)
