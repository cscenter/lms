import re
from urllib.parse import urlparse

from django.conf import settings
from django.urls import reverse as django_reverse
from django.utils.functional import lazy
from subdomains.utils import reverse as subdomain_reverse


if settings.LMS_SUBDOMAIN:
    LMS_URL_NAMESPACES = getattr(settings, "REVERSE_TO_LMS_URL_NAMESPACES", [])
    prefixes = "|".join(f"{re.escape(p)}:" for p in LMS_URL_NAMESPACES)
    starts_with_lms_subdomain = re.compile(prefixes).match

    def reverse(viewname, subdomain=None, scheme=None, args=None, kwargs=None,
                current_app=None):
        if subdomain is None and starts_with_lms_subdomain(viewname):
            subdomain = settings.LMS_SUBDOMAIN
        return subdomain_reverse(viewname, subdomain=subdomain, scheme=scheme,
                                 args=args, kwargs=kwargs,
                                 current_app=current_app)
else:
    def reverse(viewname, subdomain=None, scheme=None, args=None, kwargs=None,
                current_app=None):
        return django_reverse(viewname, args=args, kwargs=kwargs,
                              current_app=current_app)


reverse_lazy = lazy(reverse, str)


def branch_aware_reverse(viewname, subdomain=None, scheme=None, args=None,
                         kwargs=None, current_app=None):
    assert "branch_code_request" in kwargs
    if kwargs["branch_code_request"] == settings.DEFAULT_BRANCH_CODE:
        kwargs["branch_code_request"] = ""
    slash = "/" if kwargs["branch_code_request"] else ""
    kwargs["branch_trailing_slash"] = slash
    return reverse(viewname, subdomain=subdomain, scheme=scheme, args=args,
                   kwargs=kwargs, current_app=current_app)


def replace_hostname(url, new_hostname):
    """
    `core.urls.reverse` strictly related to settings.SITE_ID value, but
    management commands could send data for different domain
    """
    parsed = urlparse(url)
    replaced = parsed._replace(netloc=new_hostname,
                               scheme=settings.DEFAULT_URL_SCHEME)
    return replaced.geturl()
