from django.apps import apps
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create/update all custom SQL views in uploader.models."

    def add_arguments(self, parser):
        parser.add_argument("view",
                            default=None,
                            help="Specific SQL view to update.")

    def handle(self, *args, **options):
        if view := options["view"]:
            # Find class for this view.
            for model in apps.get_models():
                if hasattr(model, "_meta") and hasattr(model._meta, "db_table") and model._meta.db_table == view:
                    self.stdout.write(f"Creating/updating SQL view: {view}...", ending='')
                    model.update_view()
                    self.stdout.write(
                        self.style.SUCCESS("[Done]")
                    )
                    return
            raise CommandError(f"No model with view '{view}' exists.")
