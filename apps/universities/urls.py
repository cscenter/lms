from django.urls import include, path

from . import views as v

app_name = 'universities'

urlpatterns = [
    path('v1/', include(([
        path('cities/', v.CityList.as_view(), name='cities'),
        path('universities/', v.UniversityList.as_view(), name='universities'),
        path('faculties/', v.FacultyList.as_view(), name='faculties'),
    ], 'v1')))
]
