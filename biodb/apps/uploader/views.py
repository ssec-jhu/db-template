from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from biodb import __version__


@require_GET
@cache_control(max_age=60 * 60 * 24, immutable=True, public=True)  # one day
def favicon(request: HttpRequest) -> HttpResponse:
    file = (settings.STATIC_ROOT / "images" / "favicon.png").open("rb")
    return FileResponse(file)


@staff_member_required
def home(request):
    return render(request, "Home.html", context={"site_header": settings.SITE_HEADER})


def version(request):
    return HttpResponse(f"<h1>Version: '{__version__}'</h1>")
