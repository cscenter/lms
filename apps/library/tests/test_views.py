import pytest
from django.utils.encoding import smart_bytes

from auth.mixins import PermissionRequiredMixin
from core.urls import reverse
from learning.settings import Branches
from library.tests.factories import BorrowFactory, StockFactory
from users.tests.factories import UserFactory, StudentFactory, CuratorFactory


# TODO: borrows tests. Например. Убедиться, что нельзя удалить книгу, если её кто-то занял из резерва.


@pytest.mark.django_db
def test_list_view_permissions(lms_resolver):
    resolver = lms_resolver(reverse('library:book_list'))
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == "study.view_library"


@pytest.mark.django_db
def test_detail_view_permissions(lms_resolver):
    stock = StockFactory()
    resolver = lms_resolver(stock.get_absolute_url())
    assert issubclass(resolver.func.view_class, PermissionRequiredMixin)
    assert resolver.func.view_class.permission_required == "study.view_library"


@pytest.mark.django_db
def test_user_detail(client, curator):
    """Simple test for 200 http status for curators"""
    user = UserFactory()
    client.login(user)
    response = client.get(user.get_absolute_url())
    assert response.status_code == 404
    student = StudentFactory()
    client.login(student)
    response = client.get(student.get_absolute_url())
    assert response.status_code == 200
    borrow = BorrowFactory(student=student)
    response = client.get(student.get_absolute_url())
    assert response.status_code == 200
    client.login(curator)
    response = client.get(student.get_absolute_url())
    assert response.status_code == 200
    book = borrow.stock.book
    assert smart_bytes(book.title) in response.content
    borrow.stock.copies = 42
    borrow.stock.save()
    assert borrow.stock.available_copies == 41


@pytest.mark.django_db
def test_branch_support(client):
    student = StudentFactory(branch__code=Branches.SPB)
    borrow_spb = BorrowFactory(student=student,
                               stock__branch__code=Branches.SPB,
                               stock__copies=12)
    assert borrow_spb.stock.available_copies == 11
    borrow_nsk = BorrowFactory(student=student,
                               stock__branch__code=Branches.NSK,
                               stock__copies=42)
    borrow_spb.stock.refresh_from_db()
    assert borrow_spb.stock.available_copies == 11
    assert borrow_nsk.stock.available_copies == 41
    curator = CuratorFactory()
    client.login(curator)
    url = reverse('library:book_list')
    response = client.get(url)
    assert len(response.context['stocks']) == 2
    assert smart_bytes("Отделение") in response.content
    assert smart_bytes(str(Branches.get_choice(Branches.SPB).abbr)) in response.content
    assert smart_bytes(str(Branches.get_choice(Branches.NSK).abbr)) in response.content
    client.login(student)
    response = client.get(url)
    assert len(response.context['stocks']) == 1
    assert smart_bytes("Отделение") not in response.content
