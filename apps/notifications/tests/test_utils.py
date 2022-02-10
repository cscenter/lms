import pytest

from core.tests.factories import BranchFactory, SiteConfigurationFactory, SiteFactory
from notifications.management.commands.notify import get_lms_domain_name


@pytest.mark.django_db
def test_get_lms_domain_name_is_defined(settings):
    """Case when lms domain is defined in site configuration"""
    site = SiteFactory(domain='example.com')
    main_branch = BranchFactory(site=site)
    other_branch = BranchFactory(site=site, code='other')
    site_settings = SiteConfigurationFactory(site=site, lms_domain=site.domain,
                                             default_branch_code=main_branch.code)
    assert get_lms_domain_name(main_branch, site_settings) == site.domain
    assert get_lms_domain_name(other_branch, site_settings) == site.domain


@pytest.mark.parametrize("domain_name", ['example.com', 'lk.example.com'])
@pytest.mark.django_db
def test_get_lms_domain_name_is_undefined(domain_name, settings):
    site = SiteFactory(domain=domain_name)
    main_branch = BranchFactory(site=site)
    other_branch = BranchFactory(site=site, code='other')
    site_settings = SiteConfigurationFactory(site=site, lms_domain=None,
                                             default_branch_code=main_branch.code)
    assert get_lms_domain_name(main_branch, site_settings) == site.domain
    # Prepend subdomain to the url if branch != site default branch
    assert get_lms_domain_name(other_branch, site_settings) == f"{other_branch.code}.{site.domain}"
    site_settings.default_branch_code = other_branch.code
    assert get_lms_domain_name(other_branch, site_settings) == site.domain
