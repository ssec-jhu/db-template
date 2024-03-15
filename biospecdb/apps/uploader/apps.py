from django.apps import AppConfig
from django.conf import settings


class UploaderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'uploader'
    verbose_name = settings.SITE_HEADER

    def ready(self):
        import explorer.charts
        from uploader.charts import get_line_chart, get_pie_chart

        # Monkeypatch explorer charts.
        explorer.charts.get_pie_chart = get_pie_chart
        explorer.charts.get_line_chart = get_line_chart
