from django.conf import settings
from django.http import HttpResponseRedirect
from django.views import View

from compscicenter_ru.utils import PublicRoute, PublicRouteException
from core.urls import reverse


class IndexView(View):
    def get(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            redirect_to = reverse('auth:login')
        else:
            redirect_to = user.get_absolute_url(
                subdomain=settings.LMS_SUBDOMAIN)
        if user.index_redirect:
            try:
                section_code = user.index_redirect
                redirect_to = PublicRoute.url_by_code(section_code)
            except PublicRouteException:
                pass
        elif user.is_curator:
            redirect_to = reverse('staff:student_search')
        elif user.is_teacher:
            redirect_to = reverse('teaching:assignment_list')
        elif user.is_student or user.is_volunteer:
            redirect_to = reverse('study:assignment_list')
        return HttpResponseRedirect(redirect_to=redirect_to)
