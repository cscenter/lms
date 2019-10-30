from rules import predicate

from auth.permissions import add_perm, Permission
from courses.models import Course


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
