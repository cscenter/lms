import pytest

from core.urls import reverse
from universities.tests.factories import CityFactory


@pytest.mark.django_db
def test_api_view_cities(client):
    url = reverse('universities:v1:cities')
    response = client.get(url, content_type='application/json')
    assert response.status_code == 200
    assert response.json() == []
    city = CityFactory()
    response = client.get(url, content_type='application/json')
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['id'] == city.pk
    assert data[0]['name'] == city.display_name

