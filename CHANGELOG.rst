django-s3-storage changelog
===========================

0.12.4
------

- Added support for AWS KMS encryption, using the ``AWS_S3_ENCRYPT_KEY`` and ``AWS_S3_KMS_ENCRYPTION_KEY_ID`` settings.


0.12.3
------

- Actually fixed issues using ``S3Storage`` in a multithreaded environment.


0.12.2
------

- Fixed issues using ``S3Storage`` in a multithreaded environment.


0.12.1
------

- Fixed 'header does not match what was computed' error (@etianen).
- Compatibility with riak-cs (@flo-dhalluin).
- Fixed documentation typos (@mgalgs).


0.12.0
------

- Changed default for `AWS_S3_MAX_AGE_SECONDS_STATIC` to 1 hour (see https://github.com/etianen/django-s3-storage/issues/62) (@etianen, @marfire).
- Added `AWS_S3_MAX_AGE_SECONDS_CACHED_STATIC` setting (@etianen, @marfire).


0.11.3
------

- Added ``AWS_S3_SIGNATURE_VERSION`` setting.
- Changed the default signature version for S3 to v4.
  According to the `AWS documentation <http://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region>`_ all S3 regions support v4 (but not all support v2).
- Raising ``S3Error`` instead of ``OSError`` if S3 storage throws an error. ``S3Error`` inherits from both ``OSError`` and ``IOError``.
- Better checking for directory existance (@kencochrane, @etianen).
- Added ``AWS_S3_FILE_OVERWRITE `` setting (@Edke).


0.11.2
------

- Bugfix: Fixed ``listdir()`` at bucket root returning an empty list (@aaugustin).
- Added ``get_modified_time`` support (@jschneier).
- Testing against Django 1.11 (@matthiask).


0.11.1
------

- Raising ``OSError`` instead of ``IOError`` if S3 storage throws an error. On Python 3 it makes no difference, but on Python 2 it's what collectstatic expects.
- Fixed issue with ``s3_sync_meta`` where a race condition or key name normalization could cause an ``OSError`` to be raised.
- Fixed `modified_time()` on non-UTC machines.


0.11.0
------

- *Breaking:* All S3 keys are normalized to use unix-style path separators, and resolve relative paths.


0.10.0
------

- Switched to `boto3`-based implementation.
- Added `AWS_S3_CONTENT_DISPOSITION` and `AWS_S3_CONTENT_LANGUAGE` settings.
- Added `AWS_S3_CONTENT_DISPOSITION_STATIC` and `AWS_S3_CONTENT_LANGUAGE_STATIC` settings.
- *Breaking:* Setting Content-Disposition and Content-Language headers via `AWS_S3_METADATA` setting no longer supported.
- *Breaking:* `AWS_S3_HOST` setting refactored to `AWS_S3_ENDPOINT_URL`.
- *Breaking:* `AWS_S3_HOST_STATIC` setting refactored to `AWS_S3_ENDPOINT_URL_STATIC`.
- *Breaking:* `AWS_S3_CALLING_FORMAT` setting refactored to `AWS_S3_ADDRESSING_STYLE`.
- *Breaking:* `AWS_S3_CALLING_FORMAT_STATIC` setting refactored to `AWS_S3_ADDRESSING_STYLE_STATIC`.


0.9.11
------

- Added support for server-side encryption (@aaugustin).
- Allowed S3 files to be re-opened once closed (@etianen).
- Bugfixes (@Moraga, @etianen).


0.9.10
------

- Fixing regression with accessing legacy S3 keys with non-normalized path names (@etianen).


0.9.9
-----

- Added settings for disabling gzip compression (@leonsmith)
- Bug fix for relative upload paths (@leonsmith)
- Bug fix for detecting empty directories (@etianen).
- Automatic conversion of windows path separators on upload (@etianen).


0.9.8
-----

- Added support for custom metadata associated with a file (@etianen).


0.9.7
-----

- Added support for non-S3 hosts (@philippbosch, @heldinz).
- Added support for reduced redundancy storage class (@aaugustin).
- Minor bugfixes and documentation improvements (@leonsim, @alexkahn, @etianen).


0.9.6
-----

- Added settings for customizing S3 public URLs (@etianen).
- Added settings for customizing S3 calling format (@etianen).


0.9.5
-----

- Compressing javascript files on upload to S3 (@etianen).


0.9.4
-----

- Using a temporary file buffer for compressing and encoding large file uploads (@etianen).
- Eplicitly closing temporary file buffers, rather than relying on the GC (@etianen).


0.9.3
-----

- Fixed issue with s3_sync_meta management command not being included in source distribution (@etianen).


0.9.2
-----

- Added settings for fine-grained control over browser caching (@etianen).
- Added settings for adding a prefix to all keys (@etianen).


0.9.1
-----

- Added `AWS_S3_MAX_AGE_SECONDS` setting (@kasajei).
- Added option to connect S3 without AWS key/secret (@achiku).


0.9.0
-----

- First production release (@etianen).
