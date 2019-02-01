import pytest

from core.urls import reverse
from users.tests.factories import GraduateFactory


@pytest.mark.django_db
def test_testimonials(client):
    GraduateFactory(csc_review='test', photo='stub.JPG')
    response = client.get(reverse('testimonials'))
    assert response.status_code == 200
