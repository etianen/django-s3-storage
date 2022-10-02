from django.core.management.base import BaseCommand, CommandError
from django.utils.module_loading import import_string


class Command(BaseCommand):

    help = "Syncronizes the meta information on S3 files."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "storage_path",
            metavar="storage_path",
            nargs="*",
            help="Path to the Django file storage object (e.g. django.core.files.storage.default_storage).",
        )

    def handle(self, **kwargs):
        verbosity = int(kwargs.get("verbosity", 1))
        for storage_path in kwargs["storage_path"]:
            if verbosity >= 1:
                self.stdout.write(f"Syncing meta for {storage_path}")
            # Import the storage.
            try:
                storage = import_string(storage_path)
            except ImportError:
                raise CommandError(f"Could not import {storage_path}")
            # Sync the meta.
            for path in storage.sync_meta_iter():
                if verbosity >= 1:
                    self.stdout.write(f"  Synced meta for {path}")
