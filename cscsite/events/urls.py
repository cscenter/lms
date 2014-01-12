from django.conf.urls import patterns, url

from events import views

urlpatterns = \
    patterns("",
             url(regex=r"^create/$",
                 view=views.EventCreateView.as_view(),
                 name="event_create"),
             url(regex=r"^update/(?P<pk>\d+)/$",
                 view=views.EventUpdateView.as_view(),
                 name="event_update"),
             url(regex=r"^(?P<pk>\d+)/$",
                 view=views.EventDetailView.as_view(),
                 name="event_detail"),
             url(regex=r"^$",
                 view=views.EventListView.as_view(),
                 name="event_list"))

# # Same view but with a template designed to show larger list items.
# url(
#     regex=r"^large/$",
#     view=views.StuffListView.as_view(template_name="stuffage/stuff_list_large.html"),
#     name="stuff_list_large",
#     ),
