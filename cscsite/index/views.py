# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import logging
import random

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.urlresolvers import reverse

from django.db.models import Q, Count
from django.http import HttpResponseRedirect, Http404
from django.utils.timezone import now
from django.utils.translation import get_language, ugettext_lazy as _
from django.views import generic

import requests
from braces import views

from learning.models import OnlineCourse, CourseOffering, Semester, \
    StudyProgram
from learning.settings import STUDENT_STATUS
from users.models import CSCUser
from .forms import UnsubscribeForm
from .models import EnrollmentApplEmail

logger = logging.getLogger(__name__)

# TODO: move all view to core app


class IndexView(generic.TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        pool = cache.get('index_page_spb_courses_with_video')
        if pool is None:
            semester_pks = list(Semester.latest_academic_years(
                year_count=2).values_list("id", flat=True))
            pool = list(CourseOffering.custom.site_related(self.request)
                .filter(is_published_in_video=True, semester__in=semester_pks)
                .defer('description')
                .select_related('course')
                .prefetch_related('teachers', 'semester')
                .annotate(Count('courseclass')))
            cache.set('index_page_spb_courses_with_video', pool, 3600)
        random.shuffle(pool)
        context['courses'] = pool[:3]
        testimonials = cache.get('index_page_testimonials')
        if testimonials is None:
            s = (CSCUser.objects
                 .filter(groups=CSCUser.group_pks.GRADUATE_CENTER)
                 .exclude(csc_review='').exclude(photo='')
                 .order_by('?')
                 .first())
            if s and s.csc_review.strip():
                testimonials = [s]
            cache.set('index_page_testimonials', testimonials, 3600)
        context['testimonials'] = testimonials
        # Don't care about performance for online courses
        today = now().date()
        pool = list(OnlineCourse.objects.filter(Q(end__gt=today) | Q(is_self_paced=True)).order_by("start", "name").all())
        random.shuffle(pool)
        context['online_courses'] = pool[:1]
        return context


# TODO: Rewrite filter by study programs with js and 1 additional db query?
class AlumniView(generic.ListView):
    filter_by_year = None
    study_programs = None
    template_name = "users/alumni_list.html"

    def get(self, request, *args, **kwargs):
        # Validate query params
        code = self.kwargs.get("study_program_code", False)
        self.study_programs = StudyProgram.objects.all()
        if code and code not in (s.code for s in self.study_programs):
            # TODO: redirect to alumni/ page
            raise Http404
        return super(AlumniView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        user_model = get_user_model()
        graduate_pk = user_model.group_pks.GRADUATE_CENTER
        params = {
            "groups__pk": graduate_pk
        }
        if self.filter_by_year is not None:
            params["graduation_year"] = self.filter_by_year
        code = self.kwargs.get("study_program_code", False)
        if code:
            params["study_programs"] = code
        return (user_model.objects
                .filter(**params)
                .order_by("-graduation_year", "last_name", "first_name"))

    def get_context_data(self, **kwargs):
        context = super(AlumniView, self).get_context_data(**kwargs)
        code = self.kwargs.get("study_program_code", False)
        context["selected_study_program"] = code
        context["study_programs"] = self.study_programs
        if self.filter_by_year:
            context["base_url"] = reverse(
                "alumni_{}".format(self.filter_by_year))
        else:
            context["base_url"] = reverse("alumni")
        return context


class AlumniByYearView(generic.ListView):
    filter_by_year = None
    template_name = "users/alumni_by_year.html"

    def get_queryset(self):
        user_model = get_user_model()
        graduate_pk = user_model.group_pks.GRADUATE_CENTER
        params = {
            # "groups__pk": graduate_pk,
            "status": STUDENT_STATUS.will_graduate
        }
        assert self.filter_by_year is not None
        # params["graduation_year"] = self.filter_by_year
        return (user_model.objects
                .filter(**params)
                .order_by("-graduation_year", "last_name", "first_name"))

    def get_context_data(self, **kwargs):
        context = super(AlumniByYearView, self).get_context_data(**kwargs)
        testimonials = cache.get('alumni_2016_testimonials')
        if testimonials is None:
            s = (CSCUser.objects
                 .filter(
                    # groups=CSCUser.group_pks.GRADUATE_CENTER,
                    # graduation_year=self.filter_by_year,
                    status=STUDENT_STATUS.will_graduate
                 )
                 .exclude(csc_review='').exclude(photo='')
                 .order_by('?'))
            testimonials = s[:5]
            cache.set('alumni_2016_testimonials', testimonials, 3600)
        context['testimonials'] = testimonials
        return context


class RobotsView(generic.TemplateView):
    template_name = "robots.txt"

    def render_to_response(self, context, **kwargs):
        return (super(RobotsView, self)
                .render_to_response(context,
                                    content_type='text/plain',
                                    **kwargs))


class UnsubscribeYaProxyView(generic.FormView):
    template_name = "unsubscribe.html"
    form_class = UnsubscribeForm

    _results = {
        'not_found': _("Subscription wasn't found"),
        'generic_error': _("There was en error, please try again later"),
        'error_no_retry': _("There was an error, but your "
                            "subscription will be removed"),
        'ok': _("Subscription removed!")}

    def _call_ya_api_info(self, sub_hash):
        r = requests.get("https://subs-api.yandex.ru/api/1.0"
                         "/subscriptions/{}/".format(sub_hash))
        if r.status_code == 404:
            return (False, 'not_found')
        elif r.status_code != 200:
            logger.warning("Can't get subscription data: {}".format(r))
            return (False, 'generic_error')
        else:
            return (True, r.json())

    def _call_ya_api_unsub(self, sub_hash):
        r = requests.get("https://subs-api.yandex.ru/api/1.0"
                         "/subscriptions/{}/unsubscribe/".format(sub_hash))
        if r.status_code == 404:
            return 'not_found'
        if r.status_code == 500:
            logger.warning("HTTP 500 while calling Yandex API, "
                           "hash {}, response {}".format(sub_hash, r.text))
            return 'generic_error'
        r_json = r.json()
        if 'error' in r_json:
            code = r_json['error'].get('code')
            if code == 0:
                return 'generic_error'
            elif code == 2:
                return 'not_found'
            elif code == 7:
                return 'generic_error'
            elif code == 8:
                return 'error_no_retry'
            else:
                logger.warning("Yandex API returned strange code: {}"
                               .format(r_json))
                return 'generic_error'
        elif r_json.get('result') == "success":
            return 'ok'
        else:
            logger.warning("Yandex API returned strange JSON: {}"
                           .format(r_json))
            return 'generic_error'

    def get_initial(self):
        return {'sub_hash': self.kwargs['sub_hash']}

    def get_success_url(self):
        return reverse('unsubscribe_ya', args=[self.sub_hash])

    def form_valid(self, form):
        self.sub_hash = form.cleaned_data['sub_hash']
        result = self._call_ya_api_unsub(self.sub_hash)
        url = "{}?result={}".format(self.get_success_url(), result)
        return HttpResponseRedirect(url)

    def get_context_data(self, **kwargs):
        context = (super(UnsubscribeYaProxyView, self)
                   .get_context_data(**kwargs))
        redirect_result = self.request.GET.get('result')
        if redirect_result is not None:
            context['redirect'] = True
            context['text_result'] = self._results[redirect_result]
        else:
            h = self.kwargs['sub_hash']
            is_ok, result = self._call_ya_api_info(h)
            context['redirect'] = False
            if not is_ok:
                context['error'] = True
                context['text_result'] = self._results[result]
            else:
                context['error'] = False
                context['sub_hash'] = h
                context['sub_name'] = result['mail_list']['name']

            result = self._call_ya_api_unsub(h)
        return context


# FIXME: what is it?
class EnrollmentApplicationCallback(views.CsrfExemptMixin,
                                    views.JsonRequestResponseMixin,
                                    generic.View):
    require_json = True

    def post(self, request, *args, **kwargs):
        if self.request_json['secret'] == settings.GFORM_CALLBACK_SECRET:
            email = self.request_json['email']
            obj, created = (EnrollmentApplEmail.objects
                            .get_or_create(email=email))
            resp = {"status": "ok", "created": created}
            return self.render_json_response(resp)
        else:
            return self.render_json_response({"status": "auth error"})
