import pytest
from django.utils.encoding import smart_bytes

from core.urls import reverse
from library.tests.factories import BorrowFactory
from users.tests.factories import UserFactory, StudentFactory


# TODO: borrows tests. Например. Убедиться, что нельзя удалить книгу, если её кто-то занял из резерва.


@pytest.mark.django_db
def test_user_detail(client, curator):
    """Simple test for 200 http status for curators"""
    user = UserFactory()
    client.login(user)
    response = client.get(user.get_absolute_url())
    assert response.status_code == 200
    borrow = BorrowFactory(student=user)
    response = client.get(user.get_absolute_url())
    assert response.status_code == 200
    client.login(curator)
    response = client.get(user.get_absolute_url())
    assert response.status_code == 200
    book = borrow.stock.book
    assert smart_bytes(book.title) in response.content
    borrow.stock.copies = 42
    borrow.stock.save()
    assert borrow.stock.available_copies == 41


@pytest.mark.django_db
def test_city_support(client, curator):
    student = StudentFactory(city_id='spb')
    borrow_spb = BorrowFactory(student=student, stock__city_id='spb',
                               stock__copies=12)
    assert borrow_spb.stock.available_copies == 11
    borrow_nsk = BorrowFactory(student=student, stock__city_id='nsk',
                               stock__copies=42)
    borrow_spb.stock.refresh_from_db()
    assert borrow_spb.stock.available_copies == 11
    assert borrow_nsk.stock.available_copies == 41
    client.login(curator)
    url = reverse('library:book_list')
    response = client.get(url)
    assert len(response.context['stocks']) == 2
    assert smart_bytes("Город") in response.content
    assert smart_bytes("spb") in response.content
    assert smart_bytes("nsk") in response.content
    client.login(student)
    response = client.get(url)
    assert len(response.context['stocks']) == 1
    assert smart_bytes("Город") not in response.content
