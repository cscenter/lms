import pytest

from core.models import Branch
from core.tests.factories import BranchFactory, SiteFactory


@pytest.mark.django_db
def test_branch_manager_get_current(rf, settings):
    branch_code1 = 'test'
    branch_code2 = 'test2'
    branch1 = BranchFactory(code=branch_code1, site_id=settings.TEST_DOMAIN_ID)
    branch2 = BranchFactory(code=branch_code2, site_id=settings.TEST_DOMAIN_ID)
    domain1 = f"{branch_code1}.{settings.TEST_DOMAIN}"
    domain2 = f"{branch_code2}.{settings.TEST_DOMAIN}"
    request = rf.request()
    request.site = SiteFactory(domain=settings.TEST_DOMAIN)
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
    request.META['HTTP_HOST'] = "{}:8000".format(settings.TEST_DOMAIN)
    with pytest.raises(Branch.DoesNotExist):
        Branch.objects.get_current(request)
    settings.DEFAULT_BRANCH_CODE = branch_code1
    assert Branch.objects.get_current(request) == branch1
    # Without request object `get_current` method should return the default
    # branch based on settings.SITE_ID value
    assert Branch.objects.get_current() == branch1
    settings.DEFAULT_BRANCH_CODE = 'null'
    with pytest.raises(Branch.DoesNotExist):
        Branch.objects.get_current()
