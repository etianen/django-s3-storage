django-s3-storage
=================

**django-s3-storage** provides a Django Amazon S3 file storage.


Features
--------

- Django file storage for Amazon S3.
- Django static file storage for Amazon S3.
- Works in Python 3!


Installation
------------

1. Install using ``pip install django-s3-storage``.
2. Add ``'django_s3_storage'`` to your ``INSTALLED_APPS`` setting.
3. Set your ``DEFAULT_FILE_STORAGE`` setting to ``"django_s3_storage.storage.S3Storage"``.
4. Set your ``STATICFILES_STORAGE`` setting to ``"django_s3_storage.storage.StaticS3Storage"`` or ``"django_s3_storage.storage.ManifestStaticS3Storage"``.
5. Configure your Amazon S3 settings (see Available settings, below).


Authentication settings
-----------------------

Use the following settings to authenticate with Amazon AWS.

.. code:: python

    # The AWS region to connect to.
    AWS_REGION = "us-east-1"

    # The AWS access key to use.
    AWS_ACCESS_KEY_ID = ""

    # The AWS secret access key to use.
    AWS_SECRET_ACCESS_KEY = ""


File storage settings
---------------------

Use the following settings to configure the S3 file storage. You must provide at least ``AWS_S3_BUCKET_NAME``.

.. code:: python

    # The name of the bucket to store files in.
    AWS_S3_BUCKET_NAME = ""

    # How to construct S3 URLs ("auto", "path", "virtual").
    AWS_S3_ADDRESSING_STYLE = "auto"

    # The full URL to the S3 endpoint. Leave blank to use the default region URL.
    AWS_S3_ENDPOINT_URL = ""

    # A prefix to be applied to every stored file. This will be joined to every filename using the "/" separator.
    AWS_S3_KEY_PREFIX = ""

    # Whether to enable authentication for stored files. If True, then generated URLs will include an authentication
    # token valid for `AWS_S3_MAX_AGE_SECONDS`. If False, then generated URLs will not include an authentication token,
    # and their permissions will be set to "public-read".
    AWS_S3_BUCKET_AUTH = True

    # How long generated URLs are valid for. This affects the expiry of authentication tokens if `AWS_S3_BUCKET_AUTH`
    # is True. It also affects the "Cache-Control" header of the files.
    # Important: Changing this setting will not affect existing files.
    AWS_S3_MAX_AGE_SECONDS = 60 * 60  # 1 hours.

    # A URL prefix to be used for generated URLs. This is useful if your bucket is served through a CDN. This setting
    # cannot be used with `AWS_S3_BUCKET_AUTH`.
    AWS_S3_PUBLIC_URL = ""

    # If True, then files will be stored with reduced redundancy. Check the S3 documentation and make sure you
    # understand the consequences before enabling.
    # Important: Changing this setting will not affect existing files.
    AWS_S3_REDUCED_REDUNDANCY = False

    # The Content-Disposition header used when the file is downloaded. This can be a string, or a function taking a
    # single `name` argument.
    # Important: Changing this setting will not affect existing files.
    AWS_S3_CONTENT_DISPOSITION = ""

    # The Content-Language header used when the file is downloaded. This can be a string, or a function taking a
    # single `name` argument.
    # Important: Changing this setting will not affect existing files.
    AWS_S3_CONTENT_LANGUAGE = ""

    # A mapping of custom metadata for each file. Each value can be a string, or a function taking a
    # single `name` argument.
    # Important: Changing this setting will not affect existing files.
    AWS_S3_METADATA = {}

    # If True, then files will be stored using server-side encryption.
    # Important: Changing this setting will not affect existing files.
    AWS_S3_ENCRYPT_KEY = False

    # If True, then text files will be stored using gzip content encoding. Files will only be gzipped if their
    # compressed size is smaller than their uncompressed size.
    # Important: Changing this setting will not affect existing files.
    AWS_S3_GZIP = True

    # The signature version to use for S3 requests.
    AWS_S3_SIGNATURE_VERSION = None

    # If True, then files with the same name will overwrite each other. By default it's set to False to have
    # extra characters appended.
    AWS_S3_FILE_OVERWRITE =  False

**Important:** Several of these settings (noted above) will not affect existing files. To sync the new settings to
existing files, run ``./manage.py s3_sync_meta django.core.files.storage.default_storage``.


Staticfiles storage settings
----------------------------

All of the file storage settings are available for the staticfiles storage, suffixed with ``_STATIC``.
You must provide at least ``AWS_S3_BUCKET_NAME_STATIC``.

The following staticfiles storage settings have different default values to their file storage counterparts.

.. code:: python

    AWS_S3_BUCKET_AUTH_STATIC = False


The following additional staticfiles storage settings also exist:

.. code:: python

    # For ManifestStaticS3Storage, how long the browser should cache md5-hashed filenames.  This affects the expiry of
    # authentication tokens if `AWS_S3_BUCKET_AUTH` is True. It also affects the "Cache-Control" header of the files.
    # Important: Changing this setting will not affect existing files.
    AWS_S3_MAX_AGE_SECONDS_CACHED_STATIC = 60 * 60 * 24 * 265  # 1 year.


**Important:** Several of these settings (noted above) will not affect existing files. To sync the new settings to
existing files, run ``./manage.py s3_sync_meta django.contrib.staticfiles.storage.staticfiles_storage``.


Optimizing media file caching
-----------------------------

The default settings assume that media file are private. This means that they are only accessible via S3 authenticated URLs, which is bad for browser caching.

To make media files public, and enable aggressive caching, make the following changes to your ``settings.py``.

.. code:: python

    AWS_S3_BUCKET_AUTH = False

    AWS_S3_MAX_AGE_SECONDS = 60 * 60 * 24 * 365  # 1 year.

**Important:** By making these changes, all media files will be public. Ensure they do not contain confidential information.

The default settings for staticfiles storage are already optimizing for aggressive caching.


Management commands
-------------------

``s3_sync_meta``
~~~~~~~~~~~~~~~~

Syncronizes the meta information on S3 files.

Several settings (noted above) will not affect existing files. Run this command to sync the new settings to existing files.

Example usage: ``./manage.py s3_sync_meta django.core.files.storage.default_storage``


IAM permissions
---------------

In order to use all features of django-s3-storages, either authenticate with your AWS root credentials (not recommended), or create a dedicated IAM role. The minimum set of permissions required by django-s3-storage is:

.. code::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::my-bucket"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:PutObjectAcl",
                    "s3:GetObject",
                    "s3:GetObjectAcl",
                    "s3:DeleteObject"
                ],
                "Resource": [
                    "arn:aws:s3:::my-bucket/*"
                ]
            }
        ]
    }


How does django-s3-storage compare with django-storages?
--------------------------------------------------------

`django-storages <https://github.com/jschneier/django-storages>`_ supports a variety of other storage backends,
whereas django-s3-storage provides similar features, but only supports S3. It was originally written to support
Python 3 at a time when the future of django-storages was unclear. It's a small, well-tested and self-contained
library that aims to do one thing very well.

The author of django-s3-storage is not aware of significant differences in functionality with django-storages.
If you notice some differences, please file an issue!


Migration from django-storages
------------------------------

If your are updating a project that used `django-storages <https://pypi.python.org/pypi/django-storages>`_ just for S3 file storage, migration is trivial.

Follow the installation instructions, replacing 'storages' in ``INSTALLED_APPS``. Be sure to scrutinize the rest of your settings file for changes, most notably ``AWS_S3_BUCKET_NAME`` for ``AWS_STORAGE_BUCKET_NAME``.


Build status
------------

This project is built on every push using the Travis-CI service.

.. image:: https://travis-ci.org/etianen/django-s3-storage.svg?branch=master
    :target: https://travis-ci.org/etianen/django-s3-storage


Support and announcements
-------------------------

Downloads and bug tracking can be found at the `main project
website <http://github.com/etianen/django-s3-storage>`_.


More information
----------------

The django-s3-storage project was developed by Dave Hall. You can get the code
from the `django-s3-storage project site <http://github.com/etianen/django-s3-storage>`_.

Dave Hall is a freelance web developer, based in Cambridge, UK. You can usually
find him on the Internet in a number of different places:

-  `Website <http://www.etianen.com/>`_
-  `Twitter <http://twitter.com/etianen>`_
-  `Google Profile <http://www.google.com/profiles/david.etianen>`_
