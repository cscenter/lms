from django.apps import apps
from django.conf import settings
from django.contrib.admin.checks import _contains_subclass
from django.core.checks import register, Error


class Tags:
    core = "core"


@register(Tags.core)
def check_settings(app_configs, **kwargs):
    errors = []
    if getattr(settings, "LMS_SUBDOMAIN"):
        if not hasattr(settings, "SUBDOMAIN_URLCONFS"):
            errors.append(Error(
                "Add SUBDOMAIN_URLCONFS to the project's settings",
                id='core.E001',
            ))
        # check SubdomainURLRoutingMiddleware

    required_settings = [
        ("SITE_ID", 101),
        ("DEFAULT_BRANCH_CODE", 102),
        ("DEFAULT_TIMEZONE", 103),
    ]
    for attr, error_code in required_settings:
        if not hasattr(settings, attr):
            errors.append(Error(
                f"Add {attr!r} to the project's settings",
                id='core.E%d' % error_code,
            ))
    return errors


@register(Tags.core)
def check_dependencies(app_configs, **kwargs):
    errors = []
    app_dependencies = (
        ('django.contrib.sites', 201),
    )
    for app_name, error_code in app_dependencies:
        if not apps.is_installed(app_name):
            errors.append(Error(
                "'%s' must be in INSTALLED_APPS in order to use the "
                "core application" % app_name,
                id='core.E%d' % error_code,
            ))

    if not _contains_subclass('django.contrib.sites.middleware.CurrentSiteMiddleware', settings.MIDDLEWARE):
        errors.append(Error(
            "'django.contrib.sites.middleware.CurrentSiteMiddleware' must "
            "be in MIDDLEWARE in order to use the core application.",
            id='core.E301',
        ))

    return errors
