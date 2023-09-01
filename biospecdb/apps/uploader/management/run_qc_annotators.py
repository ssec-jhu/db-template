from django.core.management.base import BaseCommand, CommandError
from uploader.models import SpectralData, QCAnnotator, QCAnnotation


class Command(BaseCommand):
    help = "Run all Quality Control annotators on the SpectralData database table."

    def add_arguments(self, parser):
        parser.add_argument("no-reruns", nargs=0, default=False)

    def handle(self, *args, **options):
        try:
            all_annotators = QCAnnotator.objects.all()
        except Exception:
            raise CommandError("An error occurred when trying to retrieve all annotators")

        if not all_annotators:
            self.stdout.write(
                self.style.WARNING("No annotators exist to annotate.")
            )
            return

        try:
            all_data = SpectralData.objects.all()
        except Exception:
            raise CommandError(f"An error occurred when trying to retrieve all entries from the"
                               f" {SpectralData.__name__} table.")

        if not all_data:
            self.stdout.write(
                self.style.WARNING("No SpectralData exists to annotate.")
            )
            return

        # TODO: Care about accurate reporting of N annotators depending on whether they're default annotators.
        self.stdout.write(f"There are {len(all_annotators)} annotators and {len(all_data)} entries in the"
                          f" '{SpectralData.__name__}' table to annotate."
                          f"\nThat's {len(all_annotators) * len(all_data)} annotations in total.")

        for i, data in enumerate(all_data):
            try:
                data.annotate(force=not options["no-reruns"])
            except Exception:
                raise CommandError(f"An error occurred when running annotators for '{data}'")

            self.stdout.write(f"{i} out of {len(all_data)} completed...")  # TODO: Might not want to print everyone.

        self.stdout.write(
            self.style.SUCCESS("All annotations complete.")
        )
