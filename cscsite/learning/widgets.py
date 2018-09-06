from typing import Callable, List
import logging

import attr
from django.db.models import BooleanField, Case, Count, Value, When, Subquery
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from core.exceptions import Redirect
from core.utils import is_club_site
from learning.models import Assignment, CourseClass, CourseOfferingTeacher, \
    CourseOffering
from learning.settings import STUDENT_STATUS


logger = logging.getLogger(__name__)


@attr.s
class Tab:
    target: str = attr.ib()
    name: str = attr.ib()
    context = attr.ib(default=None)
    has_permissions: Callable = attr.ib(default=lambda u, co: False)


class TabbedPane:
    def __init__(self):
        self._tabs = {}
        self._active_tab = None

    def add(self, tab):
        if not isinstance(tab, Tab):
            raise TypeError("Provide an instance of Tab")
        self._tabs[tab.target] = tab

    def set_active_tab(self, tab):
        if tab.target not in self._tabs:
            raise ValueError(f"Can't' set tab {tab} as active")
        self._active_tab = tab

    @property
    def active_tab(self):
        return self._active_tab

    def __iter__(self):
        return iter(self._tabs)

    def items(self):
        return self._tabs.items()

    def __getitem__(self, item):
        return self._tabs[item]


class CourseOfferingTabbedPane(TabbedPane):
    """Factory for tabs pane on course offering detail page"""
    all_tabs = {
        "about": pgettext_lazy("course-tab", "About"),
        "contacts": pgettext_lazy("course-tab", "Contacts"),
        "reviews": pgettext_lazy("course-tab", "Reviews"),
        "classes": pgettext_lazy("course-tab", "Classes"),
        "assignments": pgettext_lazy("course-tab", "Assignments"),
        "news": pgettext_lazy("course-tab", "News"),
    }

    def __init__(self, course_offering):
        super().__init__()
        self._course_offering = course_offering

    def make_tabs(self, request_user, tab_to_show, redirect_to):
        """
        Generates tabs to which requested user has permission.
        If user can't access requested tab raise exception.
        """
        for target in self.all_tabs:
            tab = self.tab_factory(target)
            if tab.has_permissions(request_user, self._course_offering):
                context_method_key = f"get_{target}"
                get_context_method = getattr(self, context_method_key,
                                             lambda *args, **kwargs: None)
                tab.context = get_context_method(request_user)
                self.add(tab)
            elif target == tab_to_show:
                raise Redirect(to=redirect_to)

    @classmethod
    def tab_factory(cls, target):
        if target not in cls.all_tabs:
            raise ValueError(f"Tab with target {target} is not supported")
        has_permissions_key = f"can_view_{target}"
        has_permissions = getattr(cls, has_permissions_key, lambda u, co: False)
        return Tab(target=target, name=cls.all_tabs[target],
                   has_permissions=has_permissions)

    # FIXME: move can_view_* to permissions.py and add tests
    @staticmethod
    def can_view_about(request_user, co):
        return True

    @staticmethod
    def can_view_contacts(request_user, co):
        return request_user.get_enrollment(co.pk) or request_user.is_curator

    @staticmethod
    def can_view_reviews(request_user, co):
        return co.enrollment_is_open and (
                request_user.is_student or request_user.is_curator)

    @staticmethod
    def can_view_classes(request_user, co):
        return True

    @staticmethod
    def can_view_assignments(request_user, co):
        return (request_user.is_student or request_user.is_graduate or
                request_user.is_curator or request_user.is_teacher or
                request_user.get_enrollment(co.pk))

    @staticmethod
    def can_view_news(request_user, co):
        if is_club_site() or request_user.is_curator:
            return True
        if co.is_actual_teacher(request_user):
            return True
        if (not request_user.is_authenticated or
                request_user.status == STUDENT_STATUS.expelled):
            return False
        request_user_enrollment = request_user.get_enrollment(co.pk)
        if (request_user_enrollment and not
                co.failed_by_student(request_user, request_user_enrollment)):
            return True
        # Teachers from the same course permits to view the news
        offerings_ids = (CourseOffering.objects
                         .filter(course__slug=co.course.slug)
                         # Note: can't reset default ordering in a Subquery
                         .order_by("pk")
                         .values("pk"))
        teachers = (CourseOfferingTeacher.objects
                    .filter(course_offering__in=Subquery(offerings_ids))
                    .values_list('teacher_id', flat=True))
        return request_user.is_teacher and request_user.pk in teachers

    def get_news(self, request_user):
        return self._course_offering.courseofferingnews_set.all()
        # return {
        #     "news": news,
        #     # FIXME: нужно убрать это из таб нафигу и написать тест на unread_cnt, сейчас не ловит ничего
        #     "unread_news_cnt": news and (
        #         CourseOfferingNewsNotification.unread
        #             .filter(course_offering_news__course_offering=co, user=u)
        #             .count())
        # }

    def get_reviews(self, request_user):
        return (self._course_offering.enrollment_is_open and
                self._course_offering.get_reviews())

    def get_contacts(self, request_user):
        teachers_by_role = self._course_offering.get_grouped_teachers()
        return [ct for g in teachers_by_role.values() for ct in g
                if len(ct.teacher.private_contacts.strip()) > 0]

    def get_classes(self, request_user) -> List[CourseClass]:
        """Get course classes with attached materials"""
        classes = []
        course_classes_qs = (
            self._course_offering.courseclass_set
                .select_related("venue")
                .annotate(attachments_cnt=Count('courseclassattachment'))
                .annotate(has_attachments=Case(
                    When(attachments_cnt__gt=0, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                ))
                .order_by("date", "starts_at"))
        for cc in course_classes_qs.iterator():
            class_url = cc.get_absolute_url()
            materials = []
            if cc.slides:
                materials.append({'url': class_url + "#slides",
                                  'name': _("Slides")})
            if cc.video_url:
                materials.append({'url': class_url + "#video",
                                  'name': _("video")})
            if cc.has_attachments:
                materials.append({'url': class_url + "#attachments",
                                  'name': _("Files")})
            other_materials_embed = (
                    cc.other_materials.startswith(
                        ("<iframe src=\"https://www.slideshare",
                         "<iframe src=\"http://www.slideshare"))
                    and cc.other_materials.strip().endswith("</iframe>"))
            if cc.other_materials and not other_materials_embed:
                materials.append({'url': class_url + "#other_materials",
                                  'name': _("CourseClass|Other [materials]")})
            for m in materials:
                m['name'] = m['name'].lower()
            materials_str = ", ".join(",&nbsp;"
                                      .join(("<a href={url}>{name}</a>"
                                             .format(**x))
                                            for x in materials[i:i + 2])
                                      for i in range(0, len(materials), 2))
            materials_str = materials_str or _("No")
            setattr(cc, 'materials_str', materials_str)
            classes.append(cc)
        return classes

    def get_assignments(self, request_user) -> List[Assignment]:
        """
        For enrolled students show links to there submissions. If course
        is completed and student was enrolled in - show links to
        successfully passed assignments only.
        For course teachers (among all terms) show links to assignment details.
        For others show text only.
        """
        co = self._course_offering
        request_user_enrollment = request_user.get_enrollment(co.pk)
        co_failed_by_student = (request_user_enrollment and
                                co.failed_by_student(request_user,
                                                     request_user_enrollment))
        assignments = co.assignment_set.list()
        if request_user_enrollment is not None:
            assignments = assignments.with_progress(request_user)
        assignments = assignments.all()  # enable query caching
        for a in assignments:
            to_details = None
            if co.is_actual_teacher(request_user) or request_user.is_curator:
                to_details = reverse("assignment_detail_teacher", args=[a.pk])
            elif request_user_enrollment is not None:
                student_progress = a.studentassignment_set.first()
                if student_progress is not None:
                    # Hide link if student didn't try to solve assignment
                    # in completed course.
                    if (co_failed_by_student and
                            not student_progress.student_comments_cnt and
                            (student_progress.grade is None or student_progress.grade == 0)):
                        continue
                    to_details = student_progress.get_student_url()
                else:
                    logger.info(f"no StudentAssignment for student ID "
                                f"{request_user.pk}, assignment ID {a.pk}")
            setattr(a, 'magic_link', to_details)
        return assignments
