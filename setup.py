from setuptools import setup, find_packages

from django_s3_storage import __version__


version_str = ".".join(str(n) for n in __version__)


setup(
    name="django-s3-storage",
    version=version_str,
    license="BSD",
    description="Django Amazon S3 file storage.",
    author="Dave Hall",
    author_email="dave@etianen.com",
    url="https://github.com/etianen/django-s3-storage",
    packages=find_packages(),
    install_requires=[
        "django>=1.7",
        "boto3>=1.4.4,<2",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Framework :: Django",
    ],
)
