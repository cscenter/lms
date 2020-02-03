from rules import predicate

from auth.permissions import add_perm, Permission
from courses.models import Course, CourseClass


@add_perm
class ViewCourseNews(Permission):
    name = "courses.view_news"


@add_perm
class ChangeMetaCourse(Permission):
    name = "courses.change_metacourse"


@add_perm
class ViewCourseContacts(Permission):
    name = "courses.can_view_contacts"


@add_perm
class ViewCourseAssignments(Permission):
    name = "courses.can_view_assignments"


@add_perm
class CreateAssignment(Permission):
    name = "courses.add_assignment"


@add_perm
class CreateOwnAssignment(Permission):
    name = "teaching.add_assignment"

    @staticmethod
    @predicate
    def rule(user, course: Course):
        return any(t.teacher_id == user.pk for t in
                   course.course_teachers.all())


@add_perm
class EditAssignment(Permission):
    name = "courses.change_assignment"


@add_perm
class EditOwnAssignment(Permission):
    name = "teaching.change_own_assignment"

    @staticmethod
    @predicate
    def rule(user, course: Course):
        return any(t.teacher_id == user.pk for t in
                   course.course_teachers.all())


@add_perm
class EditCourseClass(Permission):
    name = "learning.change_courseclass"


@add_perm
class EditOwnCourseClass(Permission):
    name = "teaching.change_courseclass"

    @staticmethod
    @predicate
    def rule(user, course_class: CourseClass):
        return course_class.course.is_actual_teacher(user.pk)


@add_perm
class DeleteCourseClass(Permission):
    name = "learning.delete_courseclass"


@add_perm
class DeleteOwnCourseClass(Permission):
    name = "learning.delete_own_courseclass"

    @staticmethod
    @predicate
    def rule(user, course_class: CourseClass):
        return course_class.course.is_actual_teacher(user.pk)
