# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import logging

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.views import generic

import requests
from braces import views

from news.models import News
from .forms import UnsubscribeForm
from .models import EnrollmentApplicationEmail


logger = logging.getLogger(__name__)


class IndexView(generic.TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['news_objects'] = News.public.all()[:3]
        return context


# TODO: test it
class AlumniView(generic.ListView):
    template_name = "alumni_list.html"

    def get_queryset(self):
        user_model = get_user_model()
        graduate_pk = user_model.IS_GRADUATE_PK
        return (user_model.objects
                .filter(groups__pk=graduate_pk)
                .order_by("-graduation_year", "last_name", "first_name"))


# TODO: this view should make a distinction between professors that have active
#       courses and that who don't
# TODO: test it
class TeachersView(generic.ListView):
    template_name = "teacher_list.html"

    def get_queryset(self):
        user_model = get_user_model()
        teacher_pk = user_model.IS_TEACHER_PK
        return user_model.objects.filter(groups__pk=teacher_pk)


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


class EnrollmentApplicationCallback(views.CsrfExemptMixin,
                                    views.JsonRequestResponseMixin,
                                    generic.View):
    require_json = True

    def post(self, request, *args, **kwargs):
        print request
        print self.request_json
        logger.warning("foo: {} bar: {}".format(request, self.request_json))
        return self.render_json_response({"status": "ok"})
