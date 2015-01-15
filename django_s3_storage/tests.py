from django.test import TestCase
from unittest import skipUnless

from django_s3_storage.conf import settings


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
