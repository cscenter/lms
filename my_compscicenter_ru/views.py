from django.conf import settings
from django.http import HttpResponseRedirect
from django.views import View

from compscicenter_ru.utils import PublicRoute, PublicRouteException
from core.urls import reverse


class IndexView(View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            redirect_to = reverse('login', subdomain=settings.LMS_SUBDOMAIN)
        else:
            redirect_to = request.user.get_absolute_url()
        if request.user.index_redirect:
            try:
                section_code = request.user.index_redirect
                redirect_to = PublicRoute.url_by_code(section_code)
            except PublicRouteException:
                pass
        elif request.user.is_curator:
            redirect_to = reverse('staff:student_search')
        elif request.user.is_teacher:
            redirect_to = reverse('teaching:assignment_list')
        elif request.user.is_student:
            redirect_to = reverse('study:assignment_list')
        return HttpResponseRedirect(redirect_to=redirect_to)
