from django.conf.urls import include, url

from learning.projects.views import ReviewerProjectsView, ProjectDetailView

app_name = 'projects'
urlpatterns = [
    url(r'^projects/', include([
        url(r'^$', ReviewerProjectsView.as_view(),
            name='reviewer_projects'),
        url(r'^(?P<pk>\d+)/$', ProjectDetailView.as_view(),
            name='reviewer_project_detail'),
    ])),
]