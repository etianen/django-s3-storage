django-s3-storage changelog
===========================

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
