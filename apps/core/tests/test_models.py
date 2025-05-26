import pytest

from core.models import Branch, SiteConfiguration
from core.tests.factories import BranchFactory, SiteConfigurationFactory, SiteFactory
from core.tests.settings import TEST_DOMAIN, TEST_DOMAIN_ID


@pytest.mark.django_db
def test_manager_branch_get_current(rf, settings):
    branch_code1 = 'test'
    branch_code2 = 'test2'
    branch1 = BranchFactory(code=branch_code1, site_id=TEST_DOMAIN_ID)
    branch2 = BranchFactory(code=branch_code2, site_id=TEST_DOMAIN_ID)
    domain1 = f"{branch_code1}.{TEST_DOMAIN}"
    domain2 = f"{branch_code2}.{TEST_DOMAIN}"
    request = rf.request()
    request.site = SiteFactory(domain=TEST_DOMAIN)
    request.path = '/'
    # Should work with and without host port
    request.META['HTTP_HOST'] = "{}:8000".format(domain1)
    assert Branch.objects.get_current(request) == branch1
    request.META['HTTP_HOST'] = "{}".format(domain1)
    assert Branch.objects.get_current(request) == branch1
    request.META['HTTP_HOST'] = "{}:8000".format(domain2)
    assert Branch.objects.get_current(request) == branch2
    # The default branch with code `test3` is not added to the DB
    settings.DEFAULT_BRANCH_CODE = 'null'
    request.META['HTTP_HOST'] = "{}:8000".format(TEST_DOMAIN)
    with pytest.raises(Branch.DoesNotExist):
        Branch.objects.get_current(request)
    settings.DEFAULT_BRANCH_CODE = branch_code1
    assert Branch.objects.get_current(request) == branch1
    # Host header is not case-insensitive
    request.META['HTTP_HOST'] = "{}:8000".format(domain1.upper())
    assert Branch.objects.get_current(request) == branch1


@pytest.mark.django_db
def test_manager_site_configuration_get_current(rf, settings):
    site1 = SiteFactory(domain='example1.org')
    site_configuration1 = SiteConfigurationFactory(site=site1)
    site2 = SiteFactory(domain='example2.org')
    site_configuration2 = SiteConfigurationFactory(site=site2)
    settings.SITE_ID = site2.pk
    request = rf.request()
    request.site = site1
    request.path = '/'
    assert SiteConfiguration.objects.get_current() == site_configuration2
    assert SiteConfiguration.objects.get_current(request) == site_configuration2


@pytest.mark.django_db
def test_model_site_configuration_encrypt_decrypt(rf, settings):
    settings.SECRET_KEY = 'short'
    value = 'secret_value'
    encrypted = SiteConfiguration.encrypt(value)
    assert SiteConfiguration.decrypt(encrypted) == value
    settings.SECRET_KEY = 'hesoHHp44vRYpd#6mX$jX>6k*ue$gZhmzEE>wcF]48U'
    assert len(settings.SECRET_KEY) > 32
    value = 'secret password'
    encrypted = SiteConfiguration.encrypt(value)
    assert SiteConfiguration.decrypt(encrypted) == value
