# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from collections import OrderedDict

from loginas.utils import restore_original_login

from learning.reports import ProgressReport

try:
    import json
except ImportError:
    from django.utils import simplejson as json

from datetime import datetime, time
from itertools import chain, repeat

from braces.views import LoginRequiredMixin
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import auth

from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db.models import Prefetch
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import is_safe_url
from django.views import generic
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from icalendar import Calendar, Event, vText, vUri
from icalendar.prop import vInline
from six.moves import zip

from core.views import ProtectedFormMixin, SuperUserOnlyMixin
from learning.models import CourseClass, Assignment, StudentAssignment, \
    CourseOffering, NonCourseEvent, Semester, Enrollment
from learning.settings import LEARNING_BASE, TEACHING_BASE
from users.utils import create_timezone
from .forms import LoginForm, UserProfileForm, CSCUserReferenceCreateForm
from .models import CSCUser, CSCUserReference


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

    def get_context_data(self, **kwargs):
        context = super(LoginView, self).get_context_data(**kwargs)
        context["has_next"] = (self.redirect_field_name in self.request.POST
                               or self.redirect_field_name in self.request.GET)
        return context

    def get_success_url(self):
        redirect_to = self.request.GET.get(self.redirect_field_name)

        if not redirect_to:
            user_groups = list(
                self.request.user.groups.values_list("id", flat=True))
            if user_groups == [CSCUser.group_pks.STUDENT_CENTER]:
                redirect_to = reverse(LEARNING_BASE)
            elif user_groups == [CSCUser.group_pks.TEACHER_CENTER]:
                redirect_to = reverse(TEACHING_BASE)

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
        # FIXME: enable after bugfix in django-loginas
        # restore_original_login(request)
        auth.logout(request)
        return super(LogoutView, self).get(request, *args, **kwargs)

    def get_redirect_url(self, **kwargs):
        redirect_to = settings.LOGOUT_REDIRECT_URL

        if self.redirect_field_name in self.request.GET:
            maybe_redirect_to = self.request.GET[self.redirect_field_name]
            if is_safe_url(url=maybe_redirect_to,
                           host=self.request.get_host()):
                redirect_to = maybe_redirect_to

        return redirect_to


class TeacherDetailView(generic.DetailView):
    template_name = "users/teacher_detail.html"
    context_object_name = 'teacher'

    def get_queryset(self, *args, **kwargs):
        co_queryset = (CourseOffering.custom.site_related(self.request)
                       .select_related('semester', 'course'))
        return (auth.get_user_model()._default_manager
                .all()
                .prefetch_related(
                    Prefetch('teaching_set',
                             queryset=co_queryset.all(),
                             to_attr='course_offerings')))

    def get_context_data(self, **kwargs):
        context = super(TeacherDetailView, self).get_context_data(**kwargs)
        teacher = context[self.context_object_name]
        if not teacher.is_teacher:
            raise Http404
        return context


class UserDetailView(generic.DetailView):
    template_name = "users/user_detail.html"
    context_object_name = 'user_object'

    def get_queryset(self, *args, **kwargs):
        enrollment_queryset = Enrollment.objects.select_related(
            'course_offering',
            'course_offering__semester',
            'course_offering__course'
        )
        if not self.request.user.is_authenticated():
            enrollment_queryset = enrollment_queryset.exclude(
                grade__in=['not_graded', 'unsatisfactory'])
        co_queryset = (CourseOffering.custom.site_related(self.request)
                       .select_related('semester', 'course'))
        prefetch_list = [
            Prefetch('teaching_set', queryset=co_queryset.all()),
            'shadcourserecord_set',
            Prefetch('enrollment_set', queryset=enrollment_queryset)
        ]
        select_list = []
        if self.request.user.is_authenticated() and self.request.user.is_curator:
            prefetch_list += ['borrows',
                              'borrows__book',
                              'onlinecourserecord_set',
                              'study_programs',
                              'cscuserreference_set']
            select_list += ['comment_last_author']
        return (auth.get_user_model()._default_manager
                .all()
                .select_related(*select_list)
                .prefetch_related(*prefetch_list))

    def get_context_data(self, *args, **kwargs):
        context = super(UserDetailView, self).get_context_data(*args, **kwargs)
        u = self.request.user
        # On center site show club students only to teachers and curators
        if self.request.site.domain != settings.CLUB_DOMAIN:
            if (list(context["user_object"]._cs_group_pks) == [
                CSCUser.group_pks.STUDENT_CLUB]
                    and not(u.is_teacher or u.is_curator)):
                raise Http404

        context['is_editing_allowed'] = (u == self.object or u.is_curator)
        context['has_curator_permissions'] = u.is_curator
        context['student_projects'] = (self.object.projectstudent_set
                                       .select_related('project',
                                                       'project__semester')
                                       .order_by('project__semester__index'))
        context['current_semester'] = Semester.get_current()
        a_ss = None
        if u.is_curator:
            related = ['assignment',
                       'assignment__course_offering',
                       'assignment__course_offering__course',
                       'assignment__course_offering__semester']
            a_ss = (StudentAssignment.objects
                    .filter(student=self.object)
                    .filter(assignment__course_offering__semester_id=context['current_semester'].id)
                    .order_by('assignment__course_offering__course__name',
                              'assignment__deadline_at',
                              'assignment__title')
                    .select_related(*related))
            # NOTE(Dmitry): this is needed to skip duplicated CourseOfferings
            #               in the table (works if objs are sorted by
            #               CourseOfferings)
            a_ss = list(a_ss)
            current_co = None
            for a_s in a_ss:
                if a_s.assignment.course_offering != current_co:
                    setattr(a_s, 'hacky_co_change', True)
                    current_co = a_s.assignment.course_offering
        context['a_ss'] = a_ss
        context["initial"] = {}
        if context['is_editing_allowed']:
            context["initial"]["user_id"] = context[self.context_object_name].pk
        if context[self.context_object_name].photo:
            try:
                context["initial"]["photo"] = {
                    "url": context[self.context_object_name].photo.url,
                    "width": context[self.context_object_name].photo.width,
                    "height": context[self.context_object_name].photo.height,
                    "cropbox": context[self.context_object_name].photo_data
                }
            except (IOError, OSError):
                pass
        # Initial data for photo cropper
        context["initial"] = json.dumps(context["initial"])
        # Collect stats about successfully passed courses
        if u.is_curator:
            student = context[self.context_object_name]
            # TODO: Move to separate method and add tests
            context['total_successfully_passed'] = (
                sum(1 for c in student.enrollment_set.all() if
                    ProgressReport.is_positive_grade(c)) +
                sum(1 for c in student.shadcourserecord_set.all() if
                    ProgressReport.is_positive_grade(c)) +
                len(student.onlinecourserecord_set.all()))
            context['enrollments_in_current_term'] = sum(
                1 for e in student.enrollment_set.all() if
                e.course_offering.semester == context['current_semester'])
            student.enrollment_set.all()
        return context


class UserUpdateView(ProtectedFormMixin, generic.UpdateView):
    model = CSCUser
    template_name = "users/user_edit.html"
    form_class = UserProfileForm

    def is_form_allowed(self, user, obj):
        return obj.pk == user.pk or (user.is_authenticated() and user.is_curator)


class UserReferenceCreateView(ProtectedFormMixin, generic.CreateView):
    model = CSCUserReference
    template_name = "users/reference_add.html"
    form_class = CSCUserReferenceCreateForm

    def get_initial(self):
        initial = super(UserReferenceCreateView, self).get_initial()
        initial['signature'] = self.request.user.get_full_name()
        return initial

    def form_valid(self, form):
        form.instance.student_id = self.kwargs['pk']
        return super(UserReferenceCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('user_reference_detail',
                       args=[self.object.student_id, self.object.pk])

    def is_form_allowed(self, user, obj):
        return user.is_authenticated() and user.is_curator


class UserReferenceDetailView(SuperUserOnlyMixin, generic.DetailView):
    model = CSCUserReference
    template_name = "users/reference_detail.html"

    def get_context_data(self, *args, **kwargs):
        context = (super(UserReferenceDetailView, self)
                   .get_context_data(*args, **kwargs))
        student_info = CSCUser.objects.students_info().get(
            pk=self.object.student.pk)
        enrollments = OrderedDict()
        # From duplicated enrollments get one with higher grade
        for e in student_info.enrollments:
            if e.created > self.object.created:
                continue
            course_id = e.course_offering.course_id
            if course_id in enrollments:
                if e.grade > enrollments[course_id].grade:
                    enrollments[course_id] = e
            else:
                enrollments[course_id] = e
        context['user_enrollments'] = enrollments
        context['shads'] = filter(lambda x: x.created < self.object.created,
                                  student_info.shads)

        return context


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
                      'course_offering__semester',
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
        data = chain(zip(repeat('teaching'), context['teacher_ccs']),
                     zip(repeat('learning'), context['student_ccs']))
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
            StudentAssignment.objects
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
                            'course_offering__semester'))
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
        data = chain(zip(repeat('teaching'), context['teacher_as']),
                     zip(repeat('learning'), context['student_as']))
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
