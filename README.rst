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

::

    # The region to connect to when storing files.
    AWS_REGION = "us-east-1"

    # The AWS access key used to access the storage buckets.
    AWS_ACCESS_KEY_ID = ""

    # The AWS secret access key used to access the storage buckets.
    AWS_SECRET_ACCESS_KEY = ""

    # The S3 bucket used to store uploaded files.
    AWS_S3_BUCKET_NAME = ""

    # The S3 bucket name used to store static files.
    AWS_S3_BUCKET_NAME_STATIC = ""


How it works
------------

Uploaded user files are stored on Amazon S3 using the private access control level. When a URL for the file
is generate, querystring auth with a timeout of 1 hour is used to secure access to the file.

Static files are stored on Amazon S3 using the public access control level and aggressive caching.

Text-based files, such as HTML, XML and JSON, are stored using gzip to save space and improve download
performance.

At the moment, files stored on S3 can only be opened in read-only mode.


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
