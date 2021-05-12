import pytest

from core.urls import reverse
from users.tests.factories import UserFactory


@pytest.mark.django_db
def test_api_obtain_token(settings, client):
    url = reverse("auth-api:v1:token_obtain", subdomain=settings.LMS_SUBDOMAIN)
    response = client.post(url)
    assert response.status_code == 400
    wrong_credentials = {
        'username': 'wrong@email.ru',
        'password': 'fakePassword'
    }
    response = client.post(url, wrong_credentials)
    assert response.status_code == 400
    user = UserFactory()
    credentials = {
        'login': user.email,
        'password': user.raw_password
    }
    response = client.post(url, credentials)
    assert response.status_code == 200
    assert 'secret_token' in response.data
