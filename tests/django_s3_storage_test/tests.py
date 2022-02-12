# coding=utf-8
from __future__ import unicode_literals

import posixpath
import time
from contextlib import contextmanager
from datetime import timedelta
from io import StringIO
from urllib.parse import urlsplit, urlunsplit

import requests
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase
from django.utils import timezone
from django.utils.timezone import is_naive, make_naive, utc

from django_s3_storage.storage import S3Storage, StaticS3Storage


class TestS3Storage(SimpleTestCase):

    def tearDown(self):
        # clean up the dir
        for entry in default_storage.listdir(""):
            default_storage.delete("/".join(entry))

    # Helpers.

    @contextmanager
    def save_file(self, name="foo.txt", content=b"foo", storage=default_storage):
        name = storage.save(name, ContentFile(content, name))
        try:
            time.sleep(1)  # Let S3 process the save.
            yield name
        finally:
            storage.delete(name)

    # Configuration tets.

    def testSettingsImported(self):
        self.assertEqual(S3Storage().settings.AWS_S3_CONTENT_LANGUAGE, "")
        with self.settings(AWS_S3_CONTENT_LANGUAGE="foo"):
            self.assertEqual(S3Storage().settings.AWS_S3_CONTENT_LANGUAGE, "foo")

    def testSettingsOverwritenBySuffixedSettings(self):
        self.assertEqual(StaticS3Storage().settings.AWS_S3_CONTENT_LANGUAGE, "")
        with self.settings(AWS_S3_CONTENT_LANGUAGE="foo", AWS_S3_CONTENT_LANGUAGE_STATIC="bar"):
            self.assertEqual(StaticS3Storage().settings.AWS_S3_CONTENT_LANGUAGE, "bar")

    def testSettingsOverwrittenByKwargs(self):
        self.assertEqual(S3Storage().settings.AWS_S3_CONTENT_LANGUAGE, "")
        self.assertEqual(S3Storage(aws_s3_content_language="foo").settings.AWS_S3_CONTENT_LANGUAGE, "foo")

    def testSettingsUnknown(self):
        self.assertRaises(ImproperlyConfigured, lambda: S3Storage(
            foo=True,
        ))

    # Storage tests.

    def testOpenMissing(self):
        self.assertRaises(OSError, lambda: default_storage.open("foo.txt"))

    def testOpenWriteMode(self):
        self.assertRaises(ValueError, lambda: default_storage.open("foo.txt", "wb"))

    def testSaveAndOpen(self):
        with self.save_file() as name:
            self.assertEqual(name, "foo.txt")
            handle = default_storage.open(name)
            self.assertEqual(handle.read(), b"foo")
            # Re-open the file.
            handle.close()
            handle.open()
            self.assertEqual(handle.read(), b"foo")

    def testSaveTextMode(self):
        with self.save_file(content="foo"):
            self.assertEqual(default_storage.open("foo.txt").read(), b"foo")

    def testSaveGzipped(self):
        # Tiny files are not gzipped.
        with self.save_file():
            self.assertEqual(default_storage.meta("foo.txt").get("ContentEncoding"), None)
            self.assertEqual(default_storage.open("foo.txt").read(), b"foo")
            self.assertEqual(requests.get(default_storage.url("foo.txt")).content, b"foo")
        # Large files are gzipped.
        with self.save_file(content=b"foo" * 1000):
            self.assertEqual(default_storage.meta("foo.txt").get("ContentEncoding"), "gzip")
            self.assertEqual(default_storage.open("foo.txt").read(), b"foo" * 1000)
            self.assertEqual(requests.get(default_storage.url("foo.txt")).content, b"foo" * 1000)

    def testGzippedSize(self):
        content = "foo" * 4096
        with self.settings(AWS_S3_GZIP=False):
            name = "foo/bar.txt"
            with self.save_file(name=name, content=content):
                meta = default_storage.meta(name)
                self.assertNotEqual(meta.get("ContentEncoding", ""), "gzip")
                self.assertNotIn("uncompressed_size", meta["Metadata"])
                self.assertEqual(default_storage.size(name), len(content))
        with self.settings(AWS_S3_GZIP=True):
            name = "foo/bar.txt.gz"
            with self.save_file(name=name, content=content):
                meta = default_storage.meta(name)
                self.assertEqual(meta["ContentEncoding"], "gzip")
                self.assertIn("uncompressed_size", meta["Metadata"])
                self.assertEqual(meta["Metadata"], {"uncompressed_size": str(len(content))})
                self.assertEqual(default_storage.size(name), len(content))

    def testUrl(self):
        with self.save_file():
            url = default_storage.url("foo.txt")
            # The URL should contain query string authentication.
            self.assertTrue(urlsplit(url).query)
            response = requests.get(url)
            # The URL should be accessible, but be marked as private.
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"foo")
            self.assertEqual(response.headers["cache-control"], "private,max-age=3600")
            # With the query string removed, the URL should not be accessible.
            url_unauthenticated = urlunsplit(urlsplit(url)[:3] + ("", "",))
            response_unauthenticated = requests.get(url_unauthenticated)
            self.assertEqual(response_unauthenticated.status_code, 403)

    def testCustomUrlContentDisposition(self):
        name = "foo/bar.txt"
        with self.save_file(name=name, content="foo" * 4096):
            url = default_storage.url(name, extra_params={"ResponseContentDisposition": "attachment"})
            self.assertIn("response-content-disposition=attachment", url)
            rsp = requests.get(url)
            self.assertEqual(rsp.status_code, 200)
            self.assertIn("Content-Disposition", rsp.headers)
            self.assertEqual(rsp.headers["Content-Disposition"], "attachment")

    def testCustomUrlWhenPublicURL(self):
        with self.settings(AWS_S3_PUBLIC_URL="/foo/", AWS_S3_BUCKET_AUTH=False):
            name = "bar.txt"
            with self.save_file(name=name, content="foo" * 4096):
                self.assertRaises(
                    ValueError,
                    default_storage.url,
                    name,
                    extra_params={"ResponseContentDisposition": "attachment"})

    def testExists(self):
        self.assertFalse(default_storage.exists("foo.txt"))
        with self.save_file():
            self.assertTrue(default_storage.exists("foo.txt"))
            self.assertFalse(default_storage.exists("fo"))

    def testExistsDir(self):
        self.assertFalse(default_storage.exists("foo/"))
        with self.save_file(name="foo/bar.txt"):
            self.assertTrue(default_storage.exists("foo/"))

    def testExistsRelative(self):
        self.assertFalse(default_storage.exists("admin/css/../img/sorting-icons.svg"))
        with self.save_file("admin/img/sorting-icons.svg"):
            self.assertTrue(default_storage.exists("admin/css/../img/sorting-icons.svg"))

    def testSize(self):
        with self.save_file():
            self.assertEqual(default_storage.size("foo.txt"), 3)

    def testDelete(self):
        with self.save_file():
            self.assertTrue(default_storage.exists("foo.txt"))
            default_storage.delete("foo.txt")
        self.assertFalse(default_storage.exists("foo.txt"))

    def testCopy(self):
        with self.save_file():
            self.assertTrue(default_storage.exists("foo.txt"))
            default_storage.copy("foo.txt", "bar.txt")
            self.assertTrue(default_storage.exists("foo.txt"))
        self.assertTrue(default_storage.exists("bar.txt"))

    def testRename(self):
        with self.save_file():
            self.assertTrue(default_storage.exists("foo.txt"))
            default_storage.rename("foo.txt", "bar.txt")
            self.assertFalse(default_storage.exists("foo.txt"))
        self.assertTrue(default_storage.exists("bar.txt"))

    def testModifiedTime(self):
        with self.save_file():
            modified_time = default_storage.modified_time("foo.txt")
            # Check that the timestamps are roughly equals.
            self.assertLess(abs(modified_time - make_naive(timezone.now(), utc)), timedelta(seconds=10))
            # All other timestamps are slaved to modified time.
            self.assertEqual(default_storage.accessed_time("foo.txt"), modified_time)
            self.assertEqual(default_storage.created_time("foo.txt"), modified_time)

    def testGetModifiedTime(self):
        tzname = "America/Argentina/Buenos_Aires"
        with self.settings(USE_TZ=False, TIME_ZONE=tzname), self.save_file():
            modified_time = default_storage.get_modified_time("foo.txt")
            self.assertTrue(is_naive(modified_time))
            # Check that the timestamps are roughly equals in the correct timezone
            self.assertLess(
                abs(modified_time - timezone.now()),
                timedelta(seconds=10))
            # All other timestamps are slaved to modified time.
            self.assertEqual(default_storage.get_accessed_time("foo.txt"), modified_time)
            self.assertEqual(default_storage.get_created_time("foo.txt"), modified_time)

        with self.save_file():
            modified_time = default_storage.get_modified_time("foo.txt")
            self.assertFalse(is_naive(modified_time))
            # Check that the timestamps are roughly equals
            self.assertLess(
                abs(modified_time - timezone.now()),
                timedelta(seconds=10))
            # All other timestamps are slaved to modified time.
            self.assertEqual(default_storage.get_accessed_time("foo.txt"), modified_time)
            self.assertEqual(default_storage.get_created_time("foo.txt"), modified_time)

    def testListdir(self):
        self.assertEqual(default_storage.listdir(""), ([], []))
        self.assertEqual(default_storage.listdir("/"), ([], []))
        with self.save_file(), self.save_file(name="bar/bat.txt"):
            self.assertEqual(default_storage.listdir(""), (["bar"], ["foo.txt"]))
            self.assertEqual(default_storage.listdir("/"), (["bar"], ["foo.txt"]))
            self.assertEqual(default_storage.listdir("bar"), ([], ["bat.txt"]))
            self.assertEqual(default_storage.listdir("/bar"), ([], ["bat.txt"]))
            self.assertEqual(default_storage.listdir("bar/"), ([], ["bat.txt"]))

    def testSyncMeta(self):
        content = b"foo" * 1000
        with self.settings(AWS_S3_GZIP=False):
            with self.save_file(name="foo/bar.txt", content=content):
                meta = default_storage.meta("foo/bar.txt")
                self.assertEqual(meta["CacheControl"], "private,max-age=3600")
                self.assertEqual(meta["ContentType"], "text/plain")
                self.assertEqual(meta.get("ContentDisposition"), None)
                self.assertEqual(meta.get("ContentLanguage"), None)
                self.assertNotIn("uncompressed_size", meta["Metadata"])
                self.assertEqual(meta.get("StorageClass"), None)
                self.assertEqual(meta.get("ServerSideEncryption"), None)
                # Store new metadata.
                with self.settings(
                    AWS_S3_BUCKET_AUTH=False,
                    AWS_S3_MAX_AGE_SECONDS=9999,
                    AWS_S3_CONTENT_DISPOSITION=lambda name: "attachment; filename={}".format(name),
                    AWS_S3_CONTENT_LANGUAGE="eo",
                    AWS_S3_METADATA={
                        "foo": "bar",
                        "baz": lambda name: name,
                    },
                    AWS_S3_REDUCED_REDUNDANCY=True,
                    AWS_S3_ENCRYPT_KEY=True,
                ):
                    default_storage.sync_meta()
                # Check metadata changed.
                meta = default_storage.meta("foo/bar.txt")
                self.assertEqual(meta["CacheControl"], "public,max-age=9999")
                self.assertEqual(meta["ContentType"], "text/plain")
                self.assertEqual(meta.get("ContentDisposition"), "attachment; filename=foo/bar.txt")
                self.assertEqual(meta.get("ContentLanguage"), "eo")
                self.assertEqual(meta.get("Metadata"), {
                    "foo": "bar",
                    "baz": "foo/bar.txt",
                })
                self.assertEqual(meta["StorageClass"], "REDUCED_REDUNDANCY")
                self.assertEqual(meta["ServerSideEncryption"], "AES256")
                # Check ACL changed by removing the query string.
                url_unauthenticated = urlunsplit(urlsplit(default_storage.url("foo/bar.txt"))[:3] + ("", "",))
                response = requests.get(url_unauthenticated)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b"foo" * 1000)

    def testSyncMetaWithGzip(self):
        content = b"foo" * 1000
        with self.settings(AWS_S3_GZIP=True):
            with self.save_file(name="foo/bar.txt", content=content):
                meta = default_storage.meta("foo/bar.txt")
                self.assertEqual(meta["CacheControl"], "private,max-age=3600")
                self.assertEqual(meta["ContentType"], "text/plain")
                self.assertEqual(meta["ContentEncoding"], "gzip")
                self.assertEqual(meta.get("ContentDisposition"), None)
                self.assertEqual(meta.get("ContentLanguage"), None)
                self.assertEqual(meta["Metadata"], {"uncompressed_size": str(len(content))})
                self.assertEqual(meta.get("StorageClass"), None)
                self.assertEqual(meta.get("ServerSideEncryption"), None)
                # Store new metadata.
                with self.settings(
                    AWS_S3_BUCKET_AUTH=False,
                    AWS_S3_MAX_AGE_SECONDS=9999,
                    AWS_S3_CONTENT_DISPOSITION=lambda name: "attachment; filename={}".format(name),
                    AWS_S3_CONTENT_LANGUAGE="eo",
                    AWS_S3_METADATA={
                        "foo": "bar",
                        "baz": lambda name: name,
                    },
                    AWS_S3_REDUCED_REDUNDANCY=True,
                    AWS_S3_ENCRYPT_KEY=True,
                ):
                    default_storage.sync_meta()
                # Check metadata changed.
                meta = default_storage.meta("foo/bar.txt")
                self.assertEqual(meta["CacheControl"], "public,max-age=9999")
                self.assertEqual(meta["ContentType"], "text/plain")
                self.assertEqual(meta["ContentEncoding"], "gzip")
                self.assertEqual(meta.get("ContentDisposition"), "attachment; filename=foo/bar.txt")
                self.assertEqual(meta.get("ContentLanguage"), "eo")
                self.assertEqual(meta.get("Metadata"), {
                    "foo": "bar",
                    "baz": "foo/bar.txt",
                    "uncompressed_size": str(len(content)),
                })
                self.assertEqual(meta["StorageClass"], "REDUCED_REDUNDANCY")
                self.assertEqual(meta["ServerSideEncryption"], "AES256")
                # Check ACL changed by removing the query string.
                url_unauthenticated = urlunsplit(urlsplit(default_storage.url("foo/bar.txt"))[:3] + ("", "",))
                response = requests.get(url_unauthenticated)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b"foo" * 1000)

    def testPublicUrl(self):
        with self.settings(AWS_S3_PUBLIC_URL="/foo/", AWS_S3_BUCKET_AUTH=False):
            self.assertEqual(default_storage.url("bar.txt"), "/foo/bar.txt")

    def testEndpointUrl(self):
        with self.settings(AWS_S3_ENDPOINT_URL="https://s3.amazonaws.com"), self.save_file() as name:
            self.assertEqual(name, "foo.txt")
            self.assertEqual(default_storage.open(name).read(), b"foo")

    def testNonOverwrite(self):
        with self.save_file() as name_1, self.save_file() as name_2:
            self.assertEqual(name_1, "foo.txt")
            self.assertNotEqual(name_1, name_2)

    def testOverwrite(self):
        with self.settings(AWS_S3_FILE_OVERWRITE=True):
            with self.save_file() as name_1, self.save_file() as name_2:
                self.assertEqual(name_1, "foo.txt")
                self.assertEqual(name_2, "foo.txt")

    # Static storage tests.

    def testStaticSettings(self):
        self.assertEqual(staticfiles_storage.settings.AWS_S3_BUCKET_AUTH, False)

    # Management commands.

    def testManagementS3SyncMeta(self):
        with self.save_file():
            # Store new metadata.
            with self.settings(AWS_S3_MAX_AGE_SECONDS=9999):
                call_command("s3_sync_meta", "django.core.files.storage.default_storage", stdout=StringIO())
            # Check metadata changed.
            meta = default_storage.meta("foo.txt")
            self.assertEqual(meta["CacheControl"], "private,max-age=9999")

    def testManagementS3SyncMetaUnknownStorage(self):
        self.assertRaises(CommandError, lambda: call_command("s3_sync_meta", "foo.bar", stdout=StringIO()))

    def testManagementCollectstatic(self):
        call_command("collectstatic", interactive=False, stdout=StringIO())
        url = staticfiles_storage.url("foo.css")
        try:
            # The non-hashed name should have the default cache control.
            meta = staticfiles_storage.meta("foo.css")
            self.assertEqual(meta["CacheControl"], "public,max-age=3600")
            # The URL should not contain query string authentication.
            self.assertFalse(urlsplit(url).query)
            # The URL should contain an MD5 hash.
            self.assertRegex(url, r"foo\.[0-9a-f]{12}\.css$")
            # The hashed name should be accessible and have a huge cache control.
            response = requests.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"* { display: none; }\n")
            self.assertEqual(response.headers["cache-control"], "public,max-age=31536000")
        finally:
            staticfiles_storage.delete("staticfiles.json")
            staticfiles_storage.delete("foo.css")
            staticfiles_storage.delete(posixpath.basename(url))
