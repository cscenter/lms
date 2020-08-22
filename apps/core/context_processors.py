from django.conf import settings


def common_context(request):
    return {
        "ESTABLISHED": settings.ESTABLISHED,
        "FAVICON_PATH": settings.FAVICON_PATH,
        "LOGO_PATH": settings.LOGO_PATH,
    }


def subdomain(request):
    return {"LMS_SUBDOMAIN": getattr(settings, "LMS_SUBDOMAIN", "")}


def js_config(request):
    return {
        "CSRF_COOKIE_NAME": settings.CSRF_COOKIE_NAME,
        "SENTRY_DSN": settings.SENTRY_DSN,
    }
