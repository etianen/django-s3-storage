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


Available settings
------------------

.. code:: python

    # The region to connect to when storing files.
    AWS_REGION = "us-east-1"

    # The AWS access key used to access the storage buckets.
    AWS_ACCESS_KEY_ID = ""

    # The AWS secret access key used to access the storage buckets.
    AWS_SECRET_ACCESS_KEY = ""

    # The S3 bucket used to store uploaded files.
    AWS_S3_BUCKET_NAME = ""

    # The S3 calling format to use to connect to the bucket.
    AWS_S3_CALLING_FORMAT = "boto.s3.connection.OrdinaryCallingFormat"

    # The host to connect to (only needed if you are using a non-AWS host)
    AWS_S3_HOST = ""

    # A prefix to add to the start of all uploaded files.
    AWS_S3_KEY_PREFIX = ""

    # Whether to enable querystring authentication for uploaded files.
    AWS_S3_BUCKET_AUTH = True

    # The expire time used to access uploaded files.
    AWS_S3_MAX_AGE_SECONDS = 60*60  # 1 hour.

    # A custom URL prefix to use for public-facing URLs for uploaded files.
    AWS_S3_PUBLIC_URL = ""

    # Whether to set the storage class of uploaded files to REDUCED_REDUNDANCY.
    AWS_S3_REDUCED_REDUNDANCY = False

    # A dictionary of additional metadata to set on the uploaded files.
    # If the value is a callable, it will be called with the path of the file on S3.
    AWS_S3_METADATA = {}

    # Whether to enable gzip compression for uploaded files.
    AWS_S3_GZIP = True

    # The S3 bucket used to store static files.
    AWS_S3_BUCKET_NAME_STATIC = ""

    # The S3 calling format to use to connect to the static bucket.
    AWS_S3_CALLING_FORMAT_STATIC = "boto.s3.connection.OrdinaryCallingFormat"

    # The host to connect to for static files (only needed if you are using a non-AWS host)
    AWS_S3_HOST_STATIC = ""

    # Whether to enable querystring authentication for static files.
    AWS_S3_BUCKET_AUTH_STATIC = False

    # A prefix to add to the start of all static files.
    AWS_S3_KEY_PREFIX_STATIC = ""

    # The expire time used to access static files.
    AWS_S3_MAX_AGE_SECONDS_STATIC = 60*60*24*365  # 1 year.

    # A custom URL prefix to use for public-facing URLs for static files.
    AWS_S3_PUBLIC_URL_STATIC = ""

    # Whether to set the storage class of static files to REDUCED_REDUNDANCY.
    AWS_S3_REDUCED_REDUNDANCY_STATIC = False

    # A dictionary of additional metadata to set on the static files.
    # If the value is a callable, it will be called with the path of the file on S3.
    AWS_S3_METADATA_STATIC = {}

    # Whether to enable gzip compression for static files.
    AWS_S3_GZIP_STATIC = True


**Important:** If you change any of the ``AWS_S3_BUCKET_AUTH`` or ``AWS_S3_MAX_AGE_SECONDS`` settings, you will need
to run ``./manage.py s3_sync_meta path.to.your.storage`` before the changes will be applied to existing media files.


How it works
------------

By default, uploaded user files are stored on Amazon S3 using the private access control level. When a URL for the file
is generated, querystring auth with a timeout of 1 hour is used to secure access to the file.

By default, static files are stored on Amazon S3 using the public access control level and aggressive caching.

Text-based files, such as HTML, XML and JSON, are stored using gzip to save space and improve download
performance.

At the moment, files stored on S3 can only be opened in read-only mode.


Optimizing media file caching
-----------------------------

The default settings assume that user-uploaded file are private. This means that
they are only accessible via S3 authenticated URLs, which is bad for browser caching.

To make user-uploaded files public, and enable aggressive caching, make the following changes to your ``settings.py``.

.. code:: python

    AWS_S3_BUCKET_AUTH = False

    AWS_S3_MAX_AGE_SECONDS = 60*60*24*365  # 1 year.

**Important:** By making these changes, all user-uploaded files will be public. Ensure they do not contain confidential information.

**Important:** If you change any of the ``AWS_S3_BUCKET_AUTH`` or ``AWS_S3_MAX_AGE_SECONDS`` settings, you will need
to run ``./manage.py s3_sync_meta path.to.your.storage`` before the changes will be applied to existing media files.


Management commands
-------------------

`s3_sync_meta`
~~~~~~~~~~~~~~

Syncronizes the meta information on S3 files.

If you change any of the ``AWS_S3_BUCKET_AUTH``, ``AWS_S3_MAX_AGE_SECONDS``, or ``AWS_S3_METADATA`` settings, you will need
to run this command before the changes will be applied to existing media files.

Example usage: ``./manage.py s3_sync_meta django.core.files.storage.default_storage``


How does django-s3-storage compare with django-storages?
--------------------------------------------------------

The `django-storages-redux <https://github.com/jschneier/django-storages>`_ fork of django-storages appears to be
the most widely used S3 storage backend for Django. It also supports a variety of other storage backends.

django-s3-storage provides similar features, but only supports S3. It was originally written to support Python 3
at a time when the future of django-storages was unclear. It's a small, well-tested and self-contained library
that aims to do one thing very well.

The author of django-s3-storage is not aware of significant differences in functionality with django-storages-redux.
If you notice some differences, please file an issue!

Migration from django-storages(non-redux)
-----------------------------------------

If your are updating a project that used `django-storages <https://pypi.python.org/pypi/django-storages/1.1.8>`_ just for S3 file storage, migration is trivial.

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
