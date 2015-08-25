from django.core.management.base import BaseCommand, CommandError
from django.utils.module_loading import import_string


class Command(BaseCommand):

    help = "Syncronizes the meta information on S3 files."

    args = "[path.to.storage.instance, ...]"

    def handle(self, *storage_paths, **kwargs):
        verbosity = int(kwargs.get("verbosity", 1))
        for storage_path in storage_paths:
            if verbosity >= 1:
                self.stdout.write("Syncing meta for {}".format(storage_path))
            # Import the storage.
            try:
                storage = import_string(storage_path)
            except ImportError:
                raise CommandError("Could not import {}".format(storage_path))
            # Sync the meta.
            for path in storage.sync_meta_iter():
                if verbosity >= 1:
                    self.stdout.write("  Synced meta for {}".format(path))
