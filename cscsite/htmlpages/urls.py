from django.conf.urls import url
from htmlpages import views

urlpatterns = [
    url(r'^(?P<url>.*)$', views.flatpage, name='htmlpages.views.flatpage'),
]
