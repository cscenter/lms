import pytest

from api.permissions import CuratorAccessPermission
from core.tests.factories import BranchFactory, SiteFactory
from core.urls import reverse
from learning.settings import StudentStatuses
from users.models import StudentStatusLog
from users.tests.factories import CuratorFactory, StudentProfileFactory


@pytest.mark.django_db
def test_api_create_alumni_profiles(client, settings, lms_resolver):
    url = reverse('staff:api:create_alumni_profiles')
    resolver = lms_resolver(url)
    assert CuratorAccessPermission in resolver.func.view_class.permission_classes
    branch = BranchFactory(site=SiteFactory(pk=settings.SITE_ID))
    student_profile = StudentProfileFactory(branch=branch, status=StudentStatuses.WILL_GRADUATE)
    curator = CuratorFactory()
    client.login(curator)
    response = client.post(url, data={"graduated_on": 'wrong_format'})
    assert response.status_code == 400
    json_data = response.json()
    assert 'errors' in json_data
    assert any(error['field'] == 'graduated_on' for error in json_data['errors'])
    # Correct case
    response = client.post(url, data={"graduated_on": "2020-08-22"})
    assert response.status_code == 201
    student_profile.refresh_from_db()
    assert student_profile.status == StudentStatuses.GRADUATE
    assert StudentStatusLog.objects.count() == 1
    log_entry = StudentStatusLog.objects.get()
    assert log_entry.entry_author == curator
