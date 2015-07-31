from django.conf.urls import patterns, url

from news import views

urlpatterns = \
    patterns("",
             url(regex=r"^create/$",
                 view=views.NewsCreateView.as_view(),
                 name="news_create"),
             url(regex=r"^update/(?P<slug>[-\w]+)/$",
                 view=views.NewsUpdateView.as_view(),
                 name="news_update"),
             url(r'^rss/$', views.NewsFeed()),
             url(regex=r"^(?P<slug>[-\w]+)/$",
                 view=views.NewsDetailView.as_view(),
                 name="news_detail"),
             url(regex=r"^$",
                 view=views.NewsListView.as_view(),
                 name="news_list"))
