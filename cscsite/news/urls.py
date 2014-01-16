from django.conf.urls import patterns, url

from news import views

urlpatterns = \
    patterns("",
             url(regex=r"^create/$",
                 view=views.NewsCreateView.as_view(),
                 name="news_create"),
             url(regex=r"^update/(?P<pk>\d+)/$",
                 view=views.NewsUpdateView.as_view(),
                 name="news_update"),
             url(regex=r"^(?P<pk>\d+)/$",
                 view=views.NewsDetailView.as_view(),
                 name="news_detail"),
             url(regex=r"^$",
                 view=views.NewsListView.as_view(),
                 name="news_list"))

# # Same view but with a template designed to show larger list items.
# url(
#     regex=r"^large/$",
#     view=views.StuffListView.as_view(template_name="stuffage/stuff_list_large.html"),
#     name="stuff_list_large",
#     ),
