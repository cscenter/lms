from django.conf.urls import include, url

from surveys import views

app_name = 'surveys'

urlpatterns = [
    # FIXME: prefix looks like courses.urls.COURSE_URI? but semester_slut separated into year and type
    url(r"^(?P<course_slug>[-\w]+)/(?P<city_code>nsk|kzn|spb|)(?P<city_delimiter>/?)(?P<semester_year>\d+)-(?P<semester_type>[\w]+)/(?P<slug>[-\w]+)/", include([
        url(r"^$", views.form_detail, name='form_detail'),
        url(r"^success/$", views.form_success, name='form_success'),
    ]), kwargs={"city_aware": True})
]
