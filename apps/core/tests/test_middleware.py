from functools import partial

import pytest
from django.contrib.sites.models import Site
from django.http.response import Http404

from core.middleware import BranchViewMiddleware
from core.models import Branch
from core.tests.factories import BranchFactory
from learning.settings import Branches


@pytest.mark.django_db
def test_branch_view_middleware(rf, settings, mocker):
    branch = BranchFactory(code='xxx')
    branch_nsk = BranchFactory(code=Branches.NSK)
    branch_nsk_other = BranchFactory(code=Branches.NSK,
                                     site_id=settings.ANOTHER_DOMAIN_ID)
    request = rf.request()
    request.site = Site.objects.get(id=settings.SITE_ID)
    request.META['HTTP_HOST'] = "{}:8000".format(request.site.domain)
    request.path = '/'
    assert not hasattr(request, "branch")
    # Required `branch_code_request` and `branch_trailing_slash`
    # named arguments not found
    middleware = BranchViewMiddleware(mocker.stub(name='get_response'))
    process_view = partial(middleware.process_view, view_func=lambda: "",
                           view_args=[])
    process_view(request, view_kwargs={})
    assert not hasattr(request, "branch")
    # `branch_trailing_slash`is omitted
    process_view(request, view_kwargs={"branch_code_request": branch.code})
    assert not hasattr(request, "branch")
    response = process_view(request, view_kwargs={
        "branch_code_request": branch.code,
        "branch_trailing_slash": ""})
    assert response.status_code == 404
    assert not hasattr(request, "branch")
    process_view(request, view_kwargs={"branch_code_request": branch.code,
                                       "branch_trailing_slash": "/"})
    assert request.branch == branch
    process_view(request, view_kwargs={"branch_code_request": branch_nsk.code,
                                       "branch_trailing_slash": "/"})
    assert request.branch == branch_nsk
    process_view(request, view_kwargs={"branch_code_request": Branches.NSK,
                                       "branch_trailing_slash": "/"})
    assert request.branch == branch_nsk

    response = process_view(request, view_kwargs={
        "branch_code_request": 'unknown',
        "branch_trailing_slash": "/"})
    assert response.status_code == 404
    delattr(request, "branch")
    process_view(request, view_kwargs={"branch_code_request": "",
                                       "branch_trailing_slash": ""})
    default_branch = Branch.objects.get(code=settings.DEFAULT_BRANCH_CODE,
                                        site_id=settings.SITE_ID)
    assert request.branch == default_branch
