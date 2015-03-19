# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from datetime import datetime, time, timedelta
from itertools import chain, izip, repeat

from django.conf import settings
from django.contrib import auth
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404, HttpResponse,\
    JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views import generic
from django.utils import timezone
from django.utils.http import is_safe_url
from braces.views import LoginRequiredMixin, JSONResponseMixin

from dateutil.relativedelta import relativedelta
import icalendar
from icalendar import Calendar, Event, vText, vUri
from icalendar.prop import vInline
import pytz

from core.views import ProtectedFormMixin, StaffOnlyMixin
from learning.models import CourseClass, Assignment, AssignmentStudent, \
    CourseOffering, NonCourseEvent
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
        prefetch_list = ['teaching_set',
                         'teaching_set__semester',
                         'teaching_set__course',
                         'enrollment_set',
                         'enrollment_set__course_offering',
                         'enrollment_set__course_offering__semester',
                         'enrollment_set__course_offering__course']
        select_list = []
        if self.request.user.is_staff:
            prefetch_list += ['borrows',
                              'borrows__book',
                              'onlinecourserecord_set',
                              'shadcourserecord_set',
                              'study_programs']
            select_list += ['comment_last_author']
        return (auth.get_user_model()
                ._default_manager
                .all()
                .select_related(*select_list)
                .prefetch_related(*prefetch_list))

    def get_context_data(self, *args, **kwargs):
        context = (super(UserDetailView, self)
                   .get_context_data(*args, **kwargs))
        u = self.request.user
        context['is_extended_profile_available'] = \
            (u.is_authenticated()
             and (u == self.object
                  or u.is_teacher
                  or u.is_superuser))
        context['is_editing_allowed'] = \
            (u.is_authenticated()
             and (u == self.object
                  or u.is_superuser))
        student_projects = list(self.object.studentproject_set
                                .prefetch_related('semesters')
                                .order_by('pk'))
        for i in range(len(student_projects)):
            semesters = list(reversed(student_projects[i].semesters.all()))
            setattr(student_projects[i], 'semesters_list', semesters)
        student_projects = sorted(student_projects,
                                  key=lambda p: ((p.semesters_list[0].type
                                                  if p.semesters_list
                                                  else None),
                                                 (-p.semesters_list[0].year
                                                  if p.semesters_list
                                                  else None)),
                                  reverse=True)
        context['student_projects'] = student_projects
        if self.request.user.is_staff:
            related = ['assignment',
                       'assignment__course_offering',
                       'assignment__course_offering__course',
                       'assignment__course_offering__semester']
            a_ss = (AssignmentStudent.objects
                    .filter(student=self.object)
                    .order_by('assignment__course_offering__semester__year',
                              '-assignment__course_offering__semester__type',
                              'assignment__course_offering__course__name',
                              'assignment__deadline_at')
                    .select_related(*related))
            a_ss = list(a_ss)
            current_co = None
            for a_s in a_ss:
                if a_s.assignment.course_offering != current_co:
                    setattr(a_s, 'hacky_co_change', True)
                    current_co = a_s.assignment.course_offering
            context['a_ss'] = a_ss
        return context


class UserUpdateView(ProtectedFormMixin, generic.UpdateView):
    model = CSCUser
    template_name = "learning/simple_crispy_form.html"
    form_class = UserProfileForm

    def is_form_allowed(self, user, obj):
        return obj.pk == user.pk or user.is_superuser or user.is_staff


class JSONDataView(generic.View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({'foo': 'bar'})


class UserSearchJSONView(StaffOnlyMixin, JSONResponseMixin, generic.View):
    content_type = u"application/javascript; charset=utf-8"
    limit = 100

    def get(self, request, *args, **kwargs):
        qs = CSCUser.objects
        filtered = False

        name_qstr = request.GET.get('name', "")
        if len(name_qstr.strip()) > 0:
            qs = qs.search_names(name_qstr)
            filtered = True

        ey_qlist = request.GET.getlist('enrollment_years')
        eys = []
        for ey_str in ey_qlist:
            try:
                eys.append(int(ey_str))
            except ValueError:
                pass
        if len(eys) > 0:
            qs = qs.filter(enrollment_year__in=eys)
            filtered = True

        if not filtered:
            return self.render_json_response({
                "users": [],
                "there_is_more": False
            })

        users_list = list(qs[:self.limit + 1]
                          .values('first_name', 'last_name', 'pk'))
        for u in users_list:
            u['url'] = reverse('user_detail', args=[u['pk']])

        return self.render_json_response({
            "users": users_list[:self.limit],
            "there_is_more": len(users_list) > self.limit
        })


class UserSearchView(StaffOnlyMixin, generic.TemplateView):
    template_name = "user_search.html"

    def get_context_data(self, **kwargs):
        context = super(UserSearchView, self).get_context_data(**kwargs)
        context['json_api_uri'] = reverse('user_search_json')
        context['enrollment_years'] = (CSCUser.objects
                                       .values_list('enrollment_year', flat=True)
                                       .filter(enrollment_year__isnull=False)
                                       .order_by('enrollment_year')
                                       .distinct())
        return context


# class StudentInfoUpdateView(StaffOnlyMixin, generic.UpdateView):
#     model = StudentInfo
#     template_name = "learning/simple_crispy_form.html"
#     form_class = StudentInfoForm

#     def get_success_url(self):
#         return reverse('user_detail', args=[self.object.student_id])

#     def form_valid(self, form):
#         self.object = form.save(commit=False)
#         self.object.save(edit_author=self.request.user)
#         return HttpResponseRedirect(self.get_success_url())


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


class ICalView(generic.base.View):
    http_method_names = ['get']

    def get_context(self):
        """
        'calname' and 'caldesc' should be set by overrriding method
        """
        tz = timezone.get_current_timezone()

        min_dt = timezone.now()
        max_dt = min_dt + relativedelta(years=1)
        return {'tz': tz, 'min_dt': min_dt, 'max_dt': max_dt}

    def init_calendar(self, context):
        cal = Calendar()
        timezone_comp = create_timezone(context['tz'],
                                        context['min_dt'], context['max_dt'])
        cal.add('prodid', ("-//Computer Science Center Calendar"
                           "//compscicenter.ru//"))
        cal.add('version', '2.0')
        cal.add_component(timezone_comp)
        cal.add('X-WR-CALNAME', vText(context['calname']))
        cal.add('X-WR-CALDESC', vText(context['caldesc']))
        cal.add('calscale', 'gregorian')
        return cal

    def get_events(self, context):
        return []

    def fill_calendar(self, init_calendar, context):
        for evt_dict in self.get_events(context):
            evt = Event()
            for k, v in evt_dict.items():
                evt.add(k, v)
            init_calendar.add_component(evt)

        return init_calendar

    def get(self, request, *args, **kwargs):
        self.kwargs = kwargs
        self.request = request
        context = self.get_context()
        init_cal = self.init_calendar(context)
        cal = self.fill_calendar(init_cal, context)
        resp = HttpResponse(cal.to_ical(),
                            content_type="text/calendar; charset=UTF-8")
        resp['Content-Disposition'] \
            = "attachment; filename=\"{}\"".format(self.ical_file_name)
        return resp


class UserSpecificCalMixin(object):
    def get_context(self):
        context = super(UserSpecificCalMixin, self).get_context()

        try:
            context['user'] = (auth.get_user_model()
                               ._default_manager
                               .get(pk=self.kwargs['pk']))
        except ObjectDoesNotExist:
            raise Http404('User not found')

        return context


class ICalClassesView(UserSpecificCalMixin, ICalView):
    ical_file_name = "csc_classes.ics"

    def get_context(self):
        context = super(ICalClassesView, self).get_context()
        user = context['user']

        cc_related = ['venue',
                      'course_offering',
                      'course_offering__semester'
                      'course_offering__course']
        teacher_ccs = (
            CourseClass.objects
            .filter(course_offering__teachers=user)
            .select_related(*cc_related))
        student_ccs = (
            CourseClass.objects
            .filter(course_offering__enrolled_students=user)
            .select_related(*cc_related))

        tz = timezone.get_current_timezone()

        if len(student_ccs) + len(teacher_ccs) > 0:
            min_date = min(cc.date for cc in chain(student_ccs, teacher_ccs))
            max_date = max(cc.date for cc in chain(student_ccs, teacher_ccs))
            min_dt = tz.localize(datetime.combine(min_date, time(00, 00)))
            max_dt = (tz.localize(datetime.combine(max_date, time(23, 59)))
                      + relativedelta(years=1))
        else:
            min_dt = context['min_dt']
            max_dt = context['max_dt']

        context.update({'min_dt': min_dt,
                        'max_dt': max_dt,
                        'user': user,
                        'calname': "Занятия CSC",
                        'caldesc': ("Календарь занятий Computer "
                                    "Science Center ({})"
                                    .format(user.get_full_name())),
                        'teacher_ccs': teacher_ccs,
                        'student_ccs': student_ccs})
        return context

    def get_events(self, context):
        tz = context['tz']
        data = chain(izip(repeat('teaching'), context['teacher_ccs']),
                     izip(repeat('learning'), context['student_ccs']))
        events = []
        for cc_type, cc in data:
            uid = ("courseclasses-{}-{}@compscicenter.ru"
                   .format(cc.pk, cc_type))
            url = "http://{}{}".format(self.request.META['HTTP_HOST'],
                                       cc.get_absolute_url())
            description = "{} ({})".format(cc.description, url)
            cats = 'CSC,CLASS,{}'.format(cc_type.upper())
            dtstart = tz.localize(datetime.combine(cc.date, cc.starts_at))
            dtend = tz.localize(datetime.combine(cc.date, cc.ends_at))

            evt = {'uid': vText(uid),
                   'url': vUri(url),
                   'summary': vText(cc.name),
                   'description': vText(description),
                   'location': vText(cc.venue.address),
                   'dtstart': dtstart,
                   'dtend': dtend,
                   'dtstamp': timezone.now(),
                   'created': cc.created,
                   'last-modified': cc.modified,
                   'categories': vInline(cats)}
            events.append(evt)

        return events


class ICalAssignmentsView(UserSpecificCalMixin, ICalView):
    ical_file_name = "csc_assignments.ics"

    def get_context(self):
        context = super(ICalAssignmentsView, self).get_context()
        user = context['user']

        student_a_ss = (
            AssignmentStudent.objects
            .filter(student=user,
                    assignment__deadline_at__gt=timezone.now())
            .select_related('assignment',
                            'assignment__course_offering',
                            'assignment__course_offering__course',
                            'assignment__course_offering__semester'))
        # NOTE(Dmitry): this is hacky, but it's better to handle this here
        #               than downstream
        student_as = []
        for a_s in student_a_ss:
            a = a_s.assignment
            url = reverse('a_s_detail_student', args=[a_s.pk])
            setattr(a, 'hacky_url', url)
            student_as.append(a)

        teacher_as = list(
            Assignment.objects
            .filter(course_offering__teachers=user,
                   deadline_at__gt=timezone.now())
            .select_related('course_offering',
                            'course_offering__course',
                            'course_offering__semester',
                            'student'))
        # NOTE(Dmitry): hacky again to be consistent
        for a in teacher_as:
            url = reverse('assignment_detail_teacher', args=[a.pk])
            setattr(a, 'hacky_url', url)

        if len(student_as) + len(teacher_as) > 0:
            max_dt = (max(a.deadline_at
                          for a in chain(student_as, teacher_as))
                      + relativedelta(years=1))
        else:
            max_dt = context['max_dt']

        context.update({'max_dt': max_dt,
                        'user': user,
                        'calname': "Задания CSC",
                        'caldesc': ("Календарь сроков выполнения заданий "
                                    "Computer Science Center ({})"
                                    .format(user.get_full_name())),
                        'student_as': student_as,
                        'teacher_as': teacher_as})
        return context

    def get_events(self, context):
        tz = context['tz']
        user = context['user']
        data = chain(izip(repeat('teaching'), context['teacher_as']),
                     izip(repeat('learning'), context['student_as']))
        events = []
        for a_type, a in data:
            uid = ("assignments-{}-{}-{}@compscicenter.ru"
                   .format(user.pk, a.pk, a_type))
            summary = "{} ({})".format(a.title, a.course_offering.course.name)
            url = "http://{}{}".format(self.request.META['HTTP_HOST'],
                                       a.hacky_url)
            cats = 'CSC,ASSIGNMENT,{}'.format(a_type.upper())
            dtstart = a.deadline_at
            dtend = a.deadline_at + relativedelta(hours=1)

            evt = {'uid': vText(uid),
                   'url': vUri(url),
                   'summary': vText(summary),
                   'description': vText(url),
                   'dtstart': dtstart,
                   'dtend': dtend,
                   'dtstamp': timezone.now(),
                   'created': a.created,
                   'last-modified': a.modified,
                   'categories': vInline(cats)}
            events.append(evt)

        return events


class ICalEventsView(ICalView):
    ical_file_name = "csc_events.ics"

    def get_context(self):
        context = super(ICalEventsView, self).get_context()
        tz = context['tz']

        nces = (NonCourseEvent.objects
                .filter(date__gt=timezone.now())
                .select_related('venue'))

        if len(nces) > 0:
            max_date = max(e.date for e in nces)
            max_dt = (tz.localize(datetime.combine(max_date, time(0,0,0)))
                      + relativedelta(years=1))
        else:
            max_dt = context['max_dt']

        context.update({'max_dt': max_dt,
                        'calname': "События CSC",
                        'caldesc': ("Календарь общих событий "
                                    "Computer Science Center"),
                        'nces': nces})
        return context

    def get_events(self, context):
        tz = context['tz']
        events = []
        for nce in context['nces']:
            uid = "noncourseevents-{}@compscicenter.ru".format(nce.pk)
            url = "http://{}{}".format(self.request.META['HTTP_HOST'],
                                       nce.get_absolute_url())
            description = "{} ({})".format(nce.name, url)
            dtstart = tz.localize(datetime.combine(nce.date, nce.starts_at))
            dtend = tz.localize(datetime.combine(nce.date, nce.ends_at))

            evt = {'uid': vText(uid),
                   'url': vUri(url),
                   'summary': vText(nce.name),
                   'description': vText(description),
                   'dtstart': dtstart,
                   'dtend': dtend,
                   'dtstamp': timezone.now(),
                   'created': nce.created,
                   'last-modified': nce.modified,
                   'categories': vInline('CSC,EVENT')}
            events.append(evt)

        return events
