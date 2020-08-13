import datetime

import factory
from factory.fuzzy import FuzzyInteger, FuzzyDate

from core.tests.factories import BranchFactory
from library.models import Book, Stock, Borrow
from users.tests.factories import UserFactory


class BookFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Book

    author = factory.Sequence(lambda n: "Author%03d" % n)
    title = factory.Sequence(lambda n: "Book%03d" % n)


class StockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Stock

    book = factory.SubFactory(BookFactory)
    branch = factory.SubFactory(BranchFactory)
    copies = FuzzyInteger(0, 42)


class BorrowFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Borrow

    stock = factory.SubFactory(StockFactory)
    student = factory.SubFactory(UserFactory)
    borrowed_on = FuzzyDate(datetime.date(2016, 1, 1))
