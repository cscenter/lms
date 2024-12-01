import csv
import io
import pytest
from django.conf import settings
from django.contrib.messages import get_messages

from core.models import Branch
from core.urls import reverse
from learning.settings import StudentStatuses
from staff.tests.factories import StudentStatusLogFactory, StudentAcademicDisciplineLogFactory
from study_programs.tests.factories import AcademicDisciplineFactory
from users.tests.factories import CuratorFactory, UserFactory


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


@pytest.mark.django_db
def test_merge_users_view(client):
    url = reverse("staff:merge_users")
    user1 = UserFactory()
    user2 = UserFactory()
    response = client.post(url)
    assert response.status_code == 403
    curator = CuratorFactory()
    client.login(curator)
    response = client.post(url)
    assert response.status_code == 302
    form = {
        "minor_email": "wrong_email",
        "major_email": "other_wrong_email"
    }
    response = client.post(url, form)
    messages = [msg.message for msg in get_messages(response.wsgi_request)]
    expected_messages = ['Major User email:<br>Enter a valid email address.',
                         'Minor User email:<br>Enter a valid email address.']
    assert all(message in messages for message in expected_messages)
    form = {
        "minor_email": "non_existing@email.com",
        "major_email": "non_existing@email.com"
    }
    response = client.post(url, form)
    messages = [msg.message for msg in get_messages(response.wsgi_request)]
    expected_messages = ['Major User email:<br>There is no User with this email',
                         'Minor User email:<br>There is no User with this email',
                         'Общее:<br>Emails must not be the same']
    assert all(message in messages for message in expected_messages)
    form = {
        "minor_email": user1.email,
        "major_email": user2.email
    }
    response = client.post(url, form)
    messages = [msg.message for msg in get_messages(response.wsgi_request)]
    expected_messages = [f"Пользователи успешно объединены. <a "
                         f"href={user2.get_absolute_url()} "
                         f"target='_blank'>"
                         f"Ссылка на объединенный профиль</a>"]
    assert all(message in messages for message in expected_messages)
    

@pytest.mark.django_db
def test_badge_number_from_csv_view(client):
    url = reverse("staff:badge_number_from_csv")
    user1 = UserFactory()
    user2 = UserFactory()
    response = client.post(url)
    assert response.status_code == 403
    
    curator = CuratorFactory()
    client.login(curator)
    response = client.post(url)
    assert response.status_code == 302
    messages = [msg.message for msg in get_messages(response.wsgi_request)]
    expected_messages = ['CSV file:<br>This field is required.']
    assert all(message in messages for message in expected_messages)
    
    csv_file = io.StringIO()
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['Не Почта', 'Не Номер пропуска'])
    csv_file.seek(0)
    response = client.post(url, {'csv_file': csv_file})
    messages = [msg.message for msg in get_messages(response.wsgi_request)]
    expected_messages = ['CSV file:<br>CSV file must contain "Email" and "Badge number" columns']
    assert all(message in messages for message in expected_messages)
    
    csv_file.seek(0)
    csv_writer.writerow(['Почта', 'Номер пропуска'])
    csv_writer.writerow([user1.email, 'test badge 1'])
    csv_writer.writerow(['wrong email', 'test badge 2'])
    csv_file.seek(0)
    response = client.post(url, {'csv_file': csv_file})
    messages = [msg.message for msg in get_messages(response.wsgi_request)]
    expected_messages = ['User with email "wrong email" does not exists']
    assert all(message in messages for message in expected_messages)
    
    csv_file.seek(0)
    csv_writer.writerow(['Почта', 'Номер пропуска'])
    csv_writer.writerow([user1.email, 'test badge 1'])
    csv_writer.writerow([user2.email, 'test badge 2'])
    csv_file.seek(0)
    response = client.post(url, {'csv_file': csv_file})
    messages = [msg.message for msg in get_messages(response.wsgi_request)]
    expected_messages = ['Номера пропусков успешно выставлены. Обработано 2 пользователей']
    assert all(message in messages for message in expected_messages)
