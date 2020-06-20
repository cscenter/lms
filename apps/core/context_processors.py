from django.conf import settings


def subdomain(request):
    return {"LMS_SUBDOMAIN": getattr(settings, "LMS_SUBDOMAIN", "")}


def js_config(request):
    return {
        "CSRF_COOKIE_NAME": settings.CSRF_COOKIE_NAME,
        "SENTRY_DSN": settings.SENTRY_DSN,
    }
