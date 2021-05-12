import pytest

from django.contrib.sites.models import Site

from core.models import SiteConfiguration
from core.tests.factories import BranchFactory
from courses.tests.factories import CourseFactory
from notifications.management.commands.notify import get_domain_name


@pytest.mark.django_db
def test_get_domain_name(settings):
    site = Site.objects.get(pk=settings.SITE_ID)
    main_branch = BranchFactory(site=site)
    other_branch = BranchFactory(site=site, code='other')
    site_settings = SiteConfiguration.objects.get(site_id=site.pk)
    course = CourseFactory(main_branch=main_branch)
    site_settings.lms_subdomain = None
    site_settings.default_branch_code = main_branch.code
    assert get_domain_name(main_branch, site_settings) == site.domain
    # Include subdomain in the url if course main branch != default site branch
    assert get_domain_name(other_branch, site_settings) == f"{other_branch.code}.{site.domain}"
    site_settings.default_branch_code = other_branch.code
    assert get_domain_name(other_branch, site_settings) == site.domain
    # LMS subdomain has higher priority
    site_settings.lms_subdomain = "my"
    assert get_domain_name(main_branch, site_settings) == f"my.{site.domain}"
    site_settings.lms_subdomain = None
    # Make sure LMS subdomain is not already included in a base domain
    site_settings.lms_subdomain = 'lk'
    main_branch.site.domain = 'example.com'
    assert get_domain_name(main_branch, site_settings) == f"lk.example.com"
    main_branch.site.domain = 'lk.example.com'
    assert get_domain_name(main_branch, site_settings) == f"lk.example.com"
