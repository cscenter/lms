import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_online_courses_list(client):
    response = client.get(reverse('online_courses:list'))
    assert response.status_code == 200
