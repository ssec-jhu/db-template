from django.apps import apps
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Delete any and all orphaned data files."

    def add_arguments(self, parser):
        parser.add_argument("--dry_run",
                            action="store_true",
                            default=False,
                            help="Output files to be deleted but don't actually delete anything.")

    def handle(self, *args, **options):
        all_orphaned_files = []
        try:
            for model in apps.get_models():
                if hasattr(model, "get_orphan_files"):
                    storage, orphaned_files = model.get_orphan_files()
                    if orphaned_files:
                        all_orphaned_files.append((storage, orphaned_files))

            if not all_orphaned_files:
                self.stdout.write(self.style.WARNING("No orphaned files detected."))
                return

            n_orphaned_files = 0
            for x in all_orphaned_files:
                n_orphaned_files += len(x[1])

            # Delete orphaned files.
            n_deleted = 0
            for storage, files in all_orphaned_files:
                for file in files:
                    n_deleted += 1

                    msg = f"{n_deleted}/{n_orphaned_files} files: '{file}'..."
                    if options["dry_run"]:
                        self.stdout.write("(dry-run) " + msg)
                    else:
                        self.stdout.write(f"Deleting {msg}")
                        try:
                            storage.delete(file)
                        except FileNotFoundError:
                            continue

            if options["dry_run"]:
                self.stdout.write(self.style.SUCCESS("(dry-run) [Done] 0 files deleted"))
            else:
                self.stdout.write(self.style.SUCCESS(f"[Done] {n_deleted} files deleted"))

        except Exception as error:
            raise CommandError(f"An error occurred whilst trying to delete orphaned data files: - '{error}'")
