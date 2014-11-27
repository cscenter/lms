# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from datetime import datetime, time, timedelta
from itertools import chain, izip, repeat

from django.conf import settings
from django.contrib import auth
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views import generic
from django.utils import timezone
from django.utils.http import is_safe_url
from braces.views import LoginRequiredMixin

from dateutil.relativedelta import relativedelta
import icalendar
from icalendar import Calendar, Event, vText, vUri
from icalendar.prop import vInline
import pytz

from core.views import ProtectedFormMixin
from learning.models import CourseClass, Assignment, CourseOffering
from .forms import LoginForm, UserProfileForm
from .models import CSCUser


# inspired by https://raw2.github.com/concentricsky/django-sky-visitor/


class LoginView(generic.FormView):
    redirect_field_name = auth.REDIRECT_FIELD_NAME
    form_class = LoginForm
    template_name = "login.html"

    @method_decorator(never_cache)
    @method_decorator(sensitive_post_parameters('password'))
    def dispatch(self, *args, **kwargs):
        return super(LoginView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        # credentials were checked in AuthenticationForm.is_valid()
        auth.login(self.request, form.get_user())
        return HttpResponseRedirect(self.get_success_url())

    # TODO: redirect on user-specific page?
    def get_success_url(self):
        redirect_to = self.request.REQUEST.get(self.redirect_field_name)

        if not is_safe_url(redirect_to, self.request.get_host()):
            redirect_to = settings.LOGOUT_REDIRECT_URL

        return redirect_to

    def get(self, request, *args, **kwargs):
        self.request.session.set_test_cookie()
        return super(LoginView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            if self.request.session.test_cookie_worked():
                self.request.session.delete_test_cookie()
            return self.form_valid(form)
        else:
            self.request.session.set_test_cookie()
            return self.form_invalid(form)


class LogoutView(LoginRequiredMixin,
                 generic.RedirectView):
    redirect_field_name = auth.REDIRECT_FIELD_NAME

    def get(self, request, *args, **kwargs):
        auth.logout(request)
        return super(LogoutView, self).get(request, *args, **kwargs)

    def get_redirect_url(self, **kwargs):
        redirect_to = settings.LOGOUT_REDIRECT_URL

        if self.redirect_field_name in self.request.REQUEST:
            maybe_redirect_to = self.request.REQUEST[self.redirect_field_name]
            if is_safe_url(url=maybe_redirect_to,
                           host=self.request.get_host()):
                redirect_to = maybe_redirect_to

        return redirect_to


class TeacherDetailView(generic.DetailView):
    template_name = "teacher_detail.html"
    context_object_name = 'teacher'

    def get_queryset(self, *args, **kwargs):
        return (auth.get_user_model()
                ._default_manager
                .all()
                .prefetch_related('teaching_set',
                                  'teaching_set__semester',
                                  'teaching_set__course'))

    def get_object(self, *args, **kwargs):
        teacher = super(TeacherDetailView, self).get_object(*args, **kwargs)
        if not teacher.is_teacher:
            raise Http404
        return teacher


class UserDetailView(generic.DetailView):
    template_name = "user_detail.html"
    context_object_name = 'user_object'

    def get_queryset(self, *args, **kwargs):
        return (auth.get_user_model()
                ._default_manager
                .all()
                .select_related('overall_grade')
                .prefetch_related('teaching_set',
                                  'teaching_set__semester',
                                  'teaching_set__course',
                                  'enrollment_set',
                                  'enrollment_set__course_offering',
                                  'enrollment_set__course_offering__semester',
                                  'enrollment_set__course_offering__course'))

    def get_context_data(self, *args, **kwargs):
        context = (super(UserDetailView, self)
                   .get_context_data(*args, **kwargs))
        context['is_extended_profile_available'] = \
            (self.request.user == self.object or
             self.request.user.is_superuser)
        context['is_editing_allowed'] = \
            context['is_extended_profile_available']
        return context


class UserUpdateView(ProtectedFormMixin, generic.UpdateView):
    model = CSCUser
    template_name = "learning/simple_crispy_form.html"
    form_class = UserProfileForm

    def is_form_allowed(self, user, obj):
        return obj.pk == user.pk

    def get_context_data(self, *args, **kwargs):
        context = (super(UserUpdateView, self)
                   .get_context_data(*args, **kwargs))
        return context


# The following code has been taken from
# https://github.com/geier/khal/blob/498df2ef62a99bb1a50
# 053e982f7f23a1bfb3600/khal/khalendar/event.py
# See https://github.com/collective/icalendar/issues/44
def to_naive_utc(dtime):
    """convert a datetime object to UTC and than remove the tzinfo, if
    datetime is naive already, return it
    """
    if not hasattr(dtime, 'tzinfo') or dtime.tzinfo is None:
        return dtime

    dtime_utc = dtime.astimezone(pytz.UTC)
    dtime_naive = dtime_utc.replace(tzinfo=None)
    return dtime_naive


def create_timezone(tz, first_date=None, last_date=None):
    """
    create an icalendar vtimezone from a pytz.tzinfo

    :param tz: the timezone
    :type tz: pytz.tzinfo
    :param first_date: the very first datetime that needs to be included in the
    transition times, typically the DTSTART value of the (first recurring)
    event
    :type first_date: datetime.datetime
    :param last_date: the last datetime that needs to included, typically the
    end of the (very last) event (of a recursion set)
    :returns: timezone information
    :rtype: icalendar.Timezone()

    we currently have a problem here:

       pytz.timezones only carry the absolute dates of time zone transitions,
       not their RRULEs. This will a) make for rather bloated VTIMEZONE
       components, especially for long recurring events, b) we'll need to
       specify for which time range this VTIMEZONE should be generated and c)
       will not be valid for recurring events that go into eternity.

    Possible Solutions:

    As this information is not provided by pytz at all, there is no
    easy solution, we'd really need to ship another version of the OLSON DB.

    """

    # TODO last_date = None, recurring to infintiy

    first_date = (datetime.today() if not first_date
                  else to_naive_utc(first_date))
    last_date = datetime.today() if not last_date else to_naive_utc(last_date)
    timezone = icalendar.Timezone()
    timezone.add('TZID', tz)

    dst = {one[2]: 'DST' in two.__repr__()
           for one, two in tz._tzinfos.iteritems()}

    # looking for the first and last transition time we need to include
    first_num, last_num = 0, len(tz._utc_transition_times) - 1
    first_tt = tz._utc_transition_times[0]
    last_tt = tz._utc_transition_times[-1]
    for num, dt in enumerate(tz._utc_transition_times):
        if dt > first_tt and dt < first_date:
            first_num = num
            first_tt = dt
        if dt < last_tt and dt > last_date:
            last_num = num
            last_tt = dt

    timezones = dict()
    for num in range(first_num, last_num + 1):
        name = tz._transition_info[num][2]
        if name in timezones:
            ttime = (tz.fromutc(tz._utc_transition_times[num])
                     .replace(tzinfo=None))
            if 'RDATE' in timezones[name]:
                timezones[name]['RDATE'].dts.append(
                    icalendar.prop.vDDDTypes(ttime))
            else:
                timezones[name].add('RDATE', ttime)
            continue

        if dst[name]:
            subcomp = icalendar.TimezoneDaylight()
        else:
            subcomp = icalendar.TimezoneStandard()

        subcomp.add('TZNAME', tz._transition_info[num][2])
        subcomp.add(
            'DTSTART',
            tz.fromutc(tz._utc_transition_times[num]).replace(tzinfo=None))
        subcomp.add('TZOFFSETTO', tz._transition_info[num][0])
        subcomp.add('TZOFFSETFROM', tz._transition_info[num - 1][0])
        timezones[name] = subcomp

    for subcomp in timezones.values():
        timezone.add_component(subcomp)

    return timezone


class ICalClassesView(generic.base.View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        user_pk = kwargs['pk']

        try:
            user = (auth.get_user_model()
                    ._default_manager
                    .get(pk=user_pk))
        except ObjectDoesNotExist:
            raise Http404('User not found')

        cc_related = ['venue',
                      'course_offering',
                      'course_offering__semester'
                      'course_offering__course']
        teacher_ccs = (
            CourseClass.objects
            .filter(course_offering__teachers__pk=user_pk)
            .select_related(*cc_related))
        student_ccs = (
            CourseClass.objects
            .filter(course_offering__enrolled_students__pk=user_pk)
            .select_related(*cc_related))

        tz = timezone.get_current_timezone()

        min_date = min(cc.date for cc in chain(student_ccs, teacher_ccs))
        max_date = max(cc.date for cc in chain(student_ccs, teacher_ccs))
        min_dt = tz.localize(datetime.combine(min_date, time(00, 00)))
        max_dt = (tz.localize(datetime.combine(max_date, time(23, 59)))
                  + relativedelta(years=1))

        # NOTE(Dmitry): i18n here isn't easy, seems to require user-selected
        #               language
        # NOTE(Dmitry): see http://www.kanzaki.com/docs/ical/ and
        #               https://tools.ietf.org/html/rfc5545
        cal = Calendar()

        cal.add('prodid', ("-//Computer Science Center Calendar"
                           "//compscicenter.ru//"))
        cal.add('version', '2.0')
        cal.add_component(create_timezone(tz, min_dt, max_dt))
        cal.add('X-WR-CALNAME', vText("Занятия CSC"))
        cal.add('X-WR-CALDESC',
                vText("Календарь занятий Computer Science Center ({})"
                      .format(user.get_full_name())))
        cal.add('calscale', 'gregorian')

        for cc_type, cc in chain(izip(repeat('teaching'), teacher_ccs),
                                 izip(repeat('learning'), student_ccs)):
            uid = ("courseclasses-{}-{}@compscicenter.ru"
                   .format(cc.pk, cc_type))
            url = "http://{}{}".format(request.META['HTTP_HOST'],
                                       cc.get_absolute_url())
            description = "{} ({})".format(cc.description, url)
            cats = 'CSC,CLASS,{}'.format(cc_type.upper())
            dtstart = tz.localize(datetime.combine(cc.date, cc.starts_at))
            dtend = tz.localize(datetime.combine(cc.date, cc.ends_at))

            evt = Event()
            evt.add('uid', vText(uid))
            evt.add('url', vUri(url))
            evt.add('summary', vText(cc.name))
            evt.add('description', vText(description))
            evt.add('location', vText(cc.venue.address))
            evt.add('dtstart', dtstart)
            evt.add('dtend', dtend)
            evt.add('dtstamp', timezone.now())
            evt.add('created', cc.created)
            evt.add('last-modified', cc.modified)
            evt.add('categories', vInline(cats))
            cal.add_component(evt)
        # FIXME(Dmitry): type "text/calendar"
        resp = HttpResponse(cal.to_ical(),
                            content_type="text/calendar; charset=UTF-8")
        resp['Content-Disposition'] \
            = "attachment; filename=\"csc_classes.ics\""
        # resp = HttpResponse(cal.to_ical(), content_type="text/plain")
        return resp
