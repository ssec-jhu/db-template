from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from django.conf import settings
from django.http import FileResponse, HttpRequest, HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from biospecdb import __version__

@require_GET
@cache_control(max_age=60 * 60 * 24, immutable=True, public=True)  # one day
def favicon(request: HttpRequest) -> HttpResponse:
    file = (settings.STATIC_ROOT / "images" / "favicon.png").open("rb")
    return FileResponse(file)


@staff_member_required
def home(request):
    return render(request, 'Home.html')


def version(request):
    return HttpResponse(f"<h1>Version: '{__version__}'</h1>")
