import datetime

import factory
from factory.fuzzy import FuzzyInteger, FuzzyDate

from core.factories import CityFactory
from library.models import Book, Stock, Borrow
from users.tests.factories import UserFactory


class BookFactory(factory.DjangoModelFactory):
    class Meta:
        model = Book

    author = factory.Sequence(lambda n: "Author%03d" % n)
    title = factory.Sequence(lambda n: "Book%03d" % n)


class StockFactory(factory.DjangoModelFactory):
    class Meta:
        model = Stock

    book = factory.SubFactory(BookFactory)
    city = factory.SubFactory(CityFactory)
    copies = FuzzyInteger(0, 42)


class BorrowFactory(factory.DjangoModelFactory):
    class Meta:
        model = Borrow

    stock = factory.SubFactory(StockFactory)
    student = factory.SubFactory(UserFactory)
    borrowed_on = FuzzyDate(datetime.date(2016, 1, 1))
