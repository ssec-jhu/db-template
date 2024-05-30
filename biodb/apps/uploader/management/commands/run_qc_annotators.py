from django.core.management.base import BaseCommand, CommandError
from uploader.models import ArrayData, QCAnnotator


class Command(BaseCommand):
    help = "Run all Quality Control annotators on the ArrayData database table."

    def add_arguments(self, parser):
        parser.add_argument("--no_reruns",
                            action="store_true",
                            default=False,
                            help="Don't run annotators on existing annotations, leave computed values as is.")

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
            all_data = ArrayData.objects.all()
        except Exception:
            raise CommandError(f"An error occurred when trying to retrieve all entries from the"
                               f" {ArrayData.__name__} table.")

        if not all_data:
            self.stdout.write(
                self.style.WARNING("No ArrayData exists to annotate.")
            )
            return

        # TODO: Care about accurate reporting of N annotators depending on whether they're default annotators.
        n_annotators = all_annotators.count()
        n_data = all_data.count()
        self.stdout.write(f"There are {n_annotators} annotators and {n_data} entries in the"
                          f" '{ArrayData.__name__}' table to annotate."
                          f"\nThat's {n_annotators * n_data} annotations in total.")

        for i, data in enumerate(all_data):
            try:
                annotations = data.annotate(force=not options["no_reruns"])
                if annotations:
                    # TODO: Might not want to print everyone.
                    self.stdout.write(f"{i * len(annotations)} out of {n_data} completed...")
            except Exception:
                raise CommandError(f"An error occurred when running annotators for '{data}'")

        self.stdout.write(
            self.style.SUCCESS("Done.")
        )
