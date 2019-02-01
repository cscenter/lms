from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import BookListView, BookDetailView

app_name = 'library'
urlpatterns = [
    path("", login_required(BookListView.as_view()), name="book_list"),
    path("<int:pk>/", login_required(BookDetailView.as_view()), name="book_detail")
]
