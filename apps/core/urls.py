import re

from django.conf import settings
from django.urls import reverse as django_reverse
from django.utils.functional import lazy
from subdomains.utils import reverse as _reverse


from core.utils import is_club_site

LMS_SUBDOMAIN_NAMESPACES = ('staff', 'study', 'teaching', 'projects',
                            'surveys', 'library')
prefixes = "|".join(f"{re.escape(p)}:" for p in LMS_SUBDOMAIN_NAMESPACES)
starts_with_lms_subdomain = re.compile(prefixes).match


def reverse(viewname, subdomain=None, scheme=None, args=None, kwargs=None,
            current_app=None):
    if is_club_site():
        # For compsciclub.ru use django's relative url
        return django_reverse(viewname, args=args, kwargs=kwargs,
                              current_app=current_app)

    if subdomain is None and starts_with_lms_subdomain(viewname):
        subdomain = settings.LMS_SUBDOMAIN

    return _reverse(viewname, subdomain=subdomain, scheme=scheme,
                    args=args, kwargs=kwargs, current_app=current_app)


reverse_lazy = lazy(reverse, str)


def city_aware_reverse(viewname, subdomain=None, scheme=None, args=None,
                       kwargs=None, current_app=None):
    assert "city_code" in kwargs
    kwargs["city_delimiter"] = ""
    if kwargs["city_code"] == settings.DEFAULT_CITY_CODE or is_club_site():
        kwargs["city_code"] = ""
    if kwargs["city_code"]:
        kwargs["city_delimiter"] = "/"
    return reverse(viewname, subdomain=subdomain, scheme=scheme, args=args,
                   kwargs=kwargs, current_app=current_app)
