from django.conf import settings
from django.contrib.sites.models import Site


def common_context(request):
    return {
        "ESTABLISHED": settings.ESTABLISHED,
        "FAVICON_PATH": settings.FAVICON_PATH,
        "LOGO_PATH": settings.LOGO_PATH,
        "YANDEX_METRIKA_ID": getattr(settings, "YANDEX_METRIKA_ID", None),
    }


def subdomain(request):
    return {"LMS_SUBDOMAIN": getattr(settings, "LMS_SUBDOMAIN", "")}


def js_config(request):
    return {
        "CSRF_COOKIE_NAME": settings.CSRF_COOKIE_NAME,
        "SENTRY_DSN": settings.SENTRY_DSN,
    }


def site_context(request):
    """Add site object to the context for all views."""
    return {
        "site": Site.objects.get(pk=settings.SITE_ID)
    }
