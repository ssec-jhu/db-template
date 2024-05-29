from django.apps import apps
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create/update/drop custom SQL views in uploader.models."

    def add_arguments(self, parser):
        parser.add_argument("view",
                            help="Specific SQL view to update.")
        parser.add_argument("--drop_only",
                            action="store_true",
                            default=False,
                            help="Drop SQL view (and dependencies) but don't re-create.")

    def handle(self, *args, **options):
        if view := options["view"]:
            # Find class for this view.
            for model in apps.get_models():
                if hasattr(model, "_meta") and hasattr(model._meta, "db_table") and model._meta.db_table == view:
                    if options["drop_only"]:
                        self.stdout.write(f"Dropping SQL view: {view}...", ending='')
                    else:
                        self.stdout.write(f"Creating/updating SQL view: {view}...", ending='')
                    try:
                        if options["drop_only"]:
                            model.drop_view(drop_dependencies=True)
                        else:
                            model.update_view()
                    except Exception as error:
                        raise CommandError(f"An error occurred whilst trying to create/update the sql-view: '{view}' -"
                                           f" '{error}'")
                    self.stdout.write(
                        self.style.SUCCESS("[Done]")
                    )
                    return
            raise CommandError(f"No model with view '{view}' exists.")
