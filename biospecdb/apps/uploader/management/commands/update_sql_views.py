import inspect

from django.core.management.base import BaseCommand, CommandError

from uploader.base_models import SqlView
import uploader.models


class Command(BaseCommand):
    help = "Create/update all custom SQL views in uploader.models."

    def handle(self, *args, **options):
        for name, obj in inspect.getmembers(uploader.models):
            if isinstance(obj, type) and issubclass(obj, SqlView) and obj is not SqlView:
                self.stdout.write(f"Creating/updating SQL view: {name}...", ending='')
                try:
                    obj.update_view()
                    self.stdout.write(
                        self.style.SUCCESS("[Done]")
                    )
                except Exception as error:
                    raise CommandError(f"An error occurred whilst trying to create/update the sql-view: '{name}' -"
                                       f" '{error}'")
