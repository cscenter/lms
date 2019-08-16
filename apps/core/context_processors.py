from django.conf import settings


def subdomain(request):
    return {"LMS_SUBDOMAIN": getattr(settings, "LMS_SUBDOMAIN", "")}
