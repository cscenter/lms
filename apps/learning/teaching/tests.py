import pytest

from core.urls import reverse


@pytest.mark.django_db
def test_teaching_index_page_smoke(client):
    """Just to make sure this view doesn't return 50x error"""
    response = client.get(reverse("teaching:base"))
    assert response.status_code == 302
