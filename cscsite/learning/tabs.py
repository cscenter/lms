import logging
from typing import Callable, List

import attr
from django.db.models import BooleanField, Case, Count, Value, When, \
    IntegerField, Prefetch
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from core.exceptions import Redirect
from core.utils import is_club_site
from courses.models import Course, CourseClass, Assignment
from learning.permissions import access_role, CourseRole

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


def _prefetch_scores_for_student(queryset, student):
    """
    For each assignment prefetch requested student's score and comments
    count. Later on iterating over assignment we can get this data
    by calling `studentassignment_set.all()[0]`
    """
    from learning.models import StudentAssignment
    qs = (StudentAssignment.objects
          .only("pk", "assignment_id", "score")
          .filter(student=student)
          .annotate(student_comments_cnt=Count(
            Case(When(assignmentcomment__author_id=student.pk,
                      then=Value(1)),
                 output_field=IntegerField())))
          .order_by("pk"))  # optimize by overriding default order
    return queryset.prefetch_related(
        Prefetch("studentassignment_set", queryset=qs))


class CourseTabbedPane(TabbedPane):
    """Factory for tabs pane on course offering detail page"""
    all_tabs = {
        "about": pgettext_lazy("course-tab", "About"),
        "contacts": pgettext_lazy("course-tab", "Contacts"),
        "reviews": pgettext_lazy("course-tab", "Reviews"),
        "classes": pgettext_lazy("course-tab", "Classes"),
        "assignments": pgettext_lazy("course-tab", "Assignments"),
        "news": pgettext_lazy("course-tab", "News"),
    }

    def __init__(self, course: Course):
        super().__init__()
        self._course = course

    def make_tabs(self, request_user, tab_to_show, redirect_to):
        """
        Generates tabs to which requested user has permission.
        If user can't access requested tab raise exception.
        """
        role = access_role(course=self._course, request_user=request_user)
        for target in self.all_tabs:
            tab = self.tab_factory(target)
            if tab.has_permissions(request_user, self._course, role):
                context_method_key = f"get_{target}"
                get_context_method = getattr(self, context_method_key,
                                             lambda *args: None)
                tab.context = get_context_method(request_user, role)
                self.add(tab)
            elif target == tab_to_show:
                raise Redirect(to=redirect_to)

    @classmethod
    def tab_factory(cls, target):
        if target not in cls.all_tabs:
            raise ValueError(f"Tab with target {target} is not supported")
        has_permissions_key = f"can_view_{target}"
        has_permissions = getattr(cls, has_permissions_key,
                                  lambda **kwargs: False)
        return Tab(target=target, name=cls.all_tabs[target],
                   has_permissions=has_permissions)

    # FIXME: move can_view_* to permissions.py and add tests
    @staticmethod
    def can_view_about(*args):
        return True

    @staticmethod
    def can_view_contacts(request_user, co, request_user_role):
        return request_user.get_enrollment(co.pk) or request_user.is_curator

    @staticmethod
    def can_view_reviews(request_user, co, request_user_role):
        return co.enrollment_is_open and (
                request_user.is_student or request_user.is_curator)

    @staticmethod
    def can_view_classes(request_user, co, request_user_role):
        return True

    @staticmethod
    def can_view_assignments(request_user, co, request_user_role):
        return (request_user.is_student or request_user.is_graduate or
                request_user.is_curator or request_user.is_teacher or
                request_user.get_enrollment(co.pk))

    @staticmethod
    def can_view_news(request_user, co, request_user_role):
        if is_club_site():
            return True
        return (request_user_role is not None and
                request_user_role != CourseRole.STUDENT_RESTRICT)

    def get_news(self, request_user, request_user_role):
        return self._course.coursenews_set.all()

    def get_reviews(self, request_user, request_user_role):
        return (self._course.enrollment_is_open and
                self._course.get_reviews())

    def get_contacts(self, request_user, request_user_role):
        teachers_by_role = self._course.get_grouped_teachers()
        return [ct for g in teachers_by_role.values() for ct in g
                if len(ct.teacher.private_contacts.strip()) > 0]

    def get_classes(self, request_user, request_user_role) -> List[CourseClass]:
        """Get course classes with attached materials"""
        classes = []
        course_classes_qs = (
            self._course.courseclass_set
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

    def get_assignments(self, request_user,
                        request_user_role) -> List[Assignment]:
        """
        For enrolled students show links to there submissions.
        Course teachers (among all terms) see links to assignment details.
        Others can see only assignment names.
        """
        co = self._course
        assignments = co.assignment_set.list()
        student_roles = [CourseRole.STUDENT_REGULAR,
                         CourseRole.STUDENT_RESTRICT]
        if request_user_role in student_roles:
            assignments = _prefetch_scores_for_student(assignments, request_user)
        assignments = assignments.all()  # enable query caching
        for a in assignments:
            to_details = None
            if request_user_role in student_roles:
                assignment_progress = a.studentassignment_set.first()
                if assignment_progress is not None:
                    if request_user_role == CourseRole.STUDENT_RESTRICT:
                        # Hide the link if student didn't send any comment on
                        # assignment (first comment is considered as a solution)
                        if not assignment_progress.student_comments_cnt:
                            continue
                    to_details = assignment_progress.get_student_url()
                else:
                    logger.info(f"no StudentAssignment for student ID "
                                f"{request_user.pk}, assignment ID {a.pk}")
            elif request_user_role in [CourseRole.TEACHER, CourseRole.CURATOR]:
                to_details = reverse("assignment_detail_teacher", args=[a.pk])
            setattr(a, 'magic_link', to_details)
        return assignments
