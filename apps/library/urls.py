from __future__ import absolute_import, unicode_literals

from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from .views import BookListView, BookDetailView


urlpatterns = [
    url(r"^$", login_required(BookListView.as_view()),
        name="library_book_list"),
    url(r"(?P<pk>\d+)/", login_required(BookDetailView.as_view()),
        name="library_book_detail")
]
