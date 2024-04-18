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
                            help="Only output column names for non-observables.")
        parser.add_argument("--exclude_non_observables",
                            action="store_true",
                            default=False,
                            help="Only output column names for observables currently in the database.")
        parser.add_argument("--center",
                            default=None,
                            help="Filter observables by center name or center ID."
                                 " Defaults to global observables when center=None.")
        parser.add_argument("--category",
                            default=None,
                            help="Filter observables by category.")
        parser.add_argument("--descriptions",
                            action="store_true",
                            default=False,
                            help="Also print field.help_text and observation.description.")
        parser.add_argument("--include_instrument_fields",
                            action="store_true",
                            default=False,
                            help="Also include Instrument fields. Note: These are not used for bulk uploads, only the"
                                 " database Instrument ID is used. Therefore these aren't that useful to list."
                                 " Does nothing when used with --exclude_non_observables.")

    def handle(self, *args, **options):
        column_names = []
        try:
            # Collect observable column names.
            if not options["exclude_observables"]:
                center = options["center"]
                if center == "None":
                    queryset = uploader.models.Observable.objects.filter(center=None)
                else:
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

                if options["descriptions"]:
                    column_names.extend([(obj.alias.strip().lower(), obj.description) for obj in queryset])
                else:
                    column_names.extend([obj.alias.strip().lower() for obj in queryset])

                # Sort.
                column_names = sorted(column_names)

            # Collect all other column name info.
            if not options["exclude_non_observables"]:
                non_observables = []
                for _name, model in getmembers(uploader.models):
                    if hasattr(model, "get_column_names"):
                        if model is uploader.models.Instrument and not options["include_instrument_fields"]:
                            continue
                        non_observables.extend(model.get_column_names(help_text=options["descriptions"]))
                column_names.extend(sorted(non_observables))

            # Dedupe.
            column_names = set(column_names)

            # Print column name info.
            if options["descriptions"]:
                for name, description in column_names:
                    self.stdout.write(f"{name}, {description}")
            else:
                for name in column_names:
                    self.stdout.write(name)

        except CommandError:
            raise
        except Exception as error:
            raise CommandError(f"An error occurred whilst collecting column names: {type(error).__name__}: {error}")
