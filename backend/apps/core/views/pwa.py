from django.contrib.staticfiles import finders
from django.http import Http404, HttpResponse


def service_worker(request):
    """Serve service worker from root scope so it can control site navigations."""
    sw_path = finders.find("js/service-worker.js")
    if not sw_path:
        raise Http404("Service worker file not found")

    with open(sw_path, "rb") as sw_file:
        content = sw_file.read()

    response = HttpResponse(content, content_type="application/javascript; charset=utf-8")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response
