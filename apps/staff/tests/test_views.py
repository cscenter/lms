import pytest
from django.conf import settings

from core.models import Branch
from core.tests.factories import BranchFactory
from core.urls import reverse
from learning.settings import StudentStatuses
from staff.tests.factories import StudentStatusLogFactory, StudentAcademicDisciplineLogFactory
from study_programs.tests.factories import AcademicDisciplineFactory
from users.models import StudentTypes
from users.tests.factories import CuratorFactory


@pytest.mark.django_db
def test_enrollment_invitation_list_view(client):
    url = reverse("staff:enrollment_invitations_list")
    curator = CuratorFactory()
    client.login(curator)
    response = client.get(url)
    assert response.status_code == 302
    branch = Branch.objects.for_site(site_id=settings.SITE_ID)[0].id
    url_redirect = f"{url}?branches={branch}"
    response = client.get(url_redirect)
    assert response.status_code == 200\

@pytest.mark.django_db
def test_studentstatuslog_list_view(client):
    url = reverse("staff:status_log_list")
    curator = CuratorFactory()
    status1 = StudentStatuses.ACADEMIC_LEAVE
    status2 = StudentStatuses.REINSTATED
    StudentStatusLogFactory.create_batch(3,
                                         status=status1,
                                         former_status=status2,
                                         is_processed=False
                                         )
    StudentStatusLogFactory.create_batch(5,
                                         status=status2,
                                         former_status=status1,
                                         is_processed=True
                                         )
    client.login(curator)
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 8

    url_redirect = f"{url}?is_processed=true"
    response = client.get(url_redirect)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 5

    url_redirect = f"{url}?is_processed=false"
    response = client.get(url_redirect)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 3

    url_redirect = f"{url}?status={status2}"
    response = client.get(url_redirect)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 5

    url_redirect = f"{url}?status={status1}"
    response = client.get(url_redirect)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 3

    url_redirect = f"{url}?former_status={status1}"
    response = client.get(url_redirect)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 5

    url_redirect = f"{url}?former_status={status2}"
    response = client.get(url_redirect)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 3

    url_redirect = f"{url}?former_status={status1}&status={status1}"
    response = client.get(url_redirect)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 0

@pytest.mark.django_db
def test_studentstatuslog_list_view_mark_processed(client):
    url = reverse("staff:status_log_list") + '?mark_processed=Обработать'
    curator = CuratorFactory()
    logs = StudentStatusLogFactory.create_batch(3, is_processed=False)
    client.login(curator)
    response = client.get(url)
    assert response.status_code == 302

    for log in logs:
        log.refresh_from_db()
        assert log.is_processed

@pytest.mark.django_db
def test_studentstatuslog_list_view_download_csv(client):
    url = reverse("staff:status_log_list") + '?download_csv=Скачать'
    curator = CuratorFactory()
    StudentStatusLogFactory.create_batch(3)
    client.login(curator)
    response = client.get(url)
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv'
    rows = [row for row in response.content.decode('utf-8').split('\n') if row != '']
    assert len(rows) == 4

@pytest.mark.django_db
def test_studentacademicdisciplinelog_list_view(client):
    url = reverse("staff:academic_discipline_log_list")
    curator = CuratorFactory()
    academic_discipline1 = AcademicDisciplineFactory()
    academic_discipline2 = AcademicDisciplineFactory()
    StudentAcademicDisciplineLogFactory.create_batch(3,
                                                     academic_discipline=academic_discipline1,
                                                     former_academic_discipline=academic_discipline2,
                                                     is_processed=False
                                                     )
    StudentAcademicDisciplineLogFactory.create_batch(5,
                                                     academic_discipline=academic_discipline2,
                                                     former_academic_discipline=academic_discipline1,
                                                     is_processed=True
                                                     )
    client.login(curator)
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 8

    url_redirect = f"{url}?is_processed=true"
    response = client.get(url_redirect)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 5

    url_redirect = f"{url}?is_processed=false"
    response = client.get(url_redirect)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 3

    url_redirect = f"{url}?academic_discipline={academic_discipline2.id}"
    response = client.get(url_redirect)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 5

    url_redirect = f"{url}?academic_discipline={academic_discipline1.id}"
    response = client.get(url_redirect)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 3

    url_redirect = f"{url}?former_academic_discipline={academic_discipline1.id}"
    response = client.get(url_redirect)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 5

    url_redirect = f"{url}?former_academic_discipline={academic_discipline2.id}"
    response = client.get(url_redirect)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 3

    url_redirect = f"{url}?former_academic_discipline={academic_discipline1.id}&academic_discipline={academic_discipline1.id}"
    response = client.get(url_redirect)
    assert response.status_code == 200
    assert len(response.context_data['logs'].values()) == 0

@pytest.mark.django_db
def test_studentacademicdisciplinelog_list_view_mark_processed(client):
    url = reverse("staff:academic_discipline_log_list") + '?mark_processed=Обработать'
    curator = CuratorFactory()
    logs = StudentAcademicDisciplineLogFactory.create_batch(3, is_processed=False)
    client.login(curator)
    response = client.get(url)
    assert response.status_code == 302

    for log in logs:
        log.refresh_from_db()
        assert log.is_processed

@pytest.mark.django_db
def test_studentacademicdisciplinelog_list_view_download_csv(client):
    url = reverse("staff:academic_discipline_log_list") + '?download_csv=Скачать'
    curator = CuratorFactory()
    StudentAcademicDisciplineLogFactory.create_batch(3)
    client.login(curator)
    response = client.get(url)
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv'
    rows = [row for row in response.content.decode('utf-8').split('\n') if row != '']
    assert len(rows) == 4
