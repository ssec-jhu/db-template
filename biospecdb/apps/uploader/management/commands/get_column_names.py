from inspect import getmembers

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

import uploader.models


class Command(BaseCommand):
    help = "List all column names usable for bulk data upload files."

    def add_arguments(self, parser):
        parser.add_argument("--exclude_observables",
                            action="store_true",
                            default=False,
                            help="Only output column names for all observables currently in the database.")
        parser.add_argument("--exclude_non_observables",
                            action="store_true",
                            default=False,
                            help="Only output column names for non-observables.")
        parser.add_argument("--center",
                            default=None,
                            help="Filter observables by center name or center ID."
                                 " Defaults to global observables where center=None.")
        parser.add_argument("--category",
                            default=None,
                            help="Filter observables by category.")

    def handle(self, *args, **options):
        column_names = []
        try:
            # Collect observable column names.
            if not options["exclude_observables"]:
                center = options["center"]
                queryset = uploader.models.Observable.objects.filter(Q(center__name__iexact=center) |
                                                                     Q(center__id__iexact=center))

                if category := options["category"]:
                    # Validate category.
                    try:
                        uploader.models.Observable.Category(category)
                    except Exception:
                        raise CommandError(f"Unrecognized observable category '{category}'."
                                           f" Must be one of {[x.value for x in uploader.models.Observable.Category]}")

                    # Filter category.
                    queryset = queryset.filter(category__iexact=category)

                column_names.extend([obj.alias.strip().lower() for obj in queryset])

            # Collect all other column names.
            if not options["exclude_non_observables"]:
                for _name, model in getmembers(uploader.models):
                    if hasattr(model, "get_column_names"):
                        column_names.extend(model.get_column_names())

            # Dedupe & Sort.
            column_names = sorted(set(column_names))

            # Print column names.
            for name in column_names:
                self.stdout.write(name)

        except CommandError:
            raise
        except Exception as error:
            raise CommandError(f"An error occurred whilst collecting column names: {type(error).__name__}: {error}")
