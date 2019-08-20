from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

from auth.registry import role_registry


# TODO: Add description of each role
class Roles(DjangoChoices):
    STUDENT = C(1, _('Student'), permissions=(
        "learning.view_study_menu",
        "courses.can_view_contacts",
        "courses.can_view_assignments",
        "learning.view_course_news",
        "learning.view_course_reviews",
        "study.view_own_enrollments",
        "study.view_own_assignments",
        "study.view_own_assignment",
        "study.create_assignment_comment",
        "study.view_courses",
        "study.view_schedule",
        "study.view_faq",
        "study.view_library",
        "study.view_internships",
        "learning.enroll_in_course",
        "learning.enroll_in_course_by_invitation",
        "learning.leave_course",
    ))
    TEACHER = C(2, _('Teacher'), permissions=(
        "learning.view_teaching_menu",
        "courses.can_view_contacts",
        "courses.can_view_assignments",
        "learning.view_course_news",
        "teaching.create_assignment_comment",
        "teaching.view_own_gradebook",
    ))
    GRADUATE = C(3, _('Graduate'), permissions=(
        "study.view_own_enrollments",
        "study.view_own_assignment",
    ))
    VOLUNTEER = C(4, _('Volunteer'), permissions=(
        "learning.view_study_menu",
        "courses.can_view_contacts",
        "courses.can_view_assignments",
        "learning.view_course_news",
        "learning.view_course_reviews",
        "study.view_own_enrollments",
        "study.view_own_assignments",
        "study.view_own_assignment",
        "study.create_assignment_comment",
        "study.view_courses",
        "study.view_schedule",
        "study.view_faq",
        "study.view_library",
        "study.view_internships",
        "learning.enroll_in_course",
        "learning.enroll_in_course_by_invitation",
        "learning.leave_course",
    ))
    CURATOR = C(5, _('Curator'), permissions=(
        "courses.change_metacourse",
        "courses.can_view_contacts",
        "courses.can_view_assignments",
        "learning.view_course_news",
        "learning.view_course_reviews",
        "study.view_library",
        "teaching.create_assignment_comment",
        "teaching.view_gradebook",
    ))
    INVITED = C(11, _('Invited User'), permissions=(
        "learning.view_study_menu",
        "courses.can_view_contacts",
        "courses.can_view_assignments",
        "learning.view_course_news",
        "learning.view_course_reviews",
        "study.view_own_enrollments",
        "study.view_own_assignments",
        "study.view_own_assignment",
        "study.create_assignment_comment",
        "study.view_courses",
        "study.view_schedule",
        "study.view_faq",
        "study.view_library",
        "study.view_internships",
        "learning.enroll_in_course_by_invitation",
        "learning.leave_course",
    ))


role_registry.register(Roles.STUDENT,
                       Roles.get_choice(Roles.STUDENT).permissions)
role_registry.register(Roles.TEACHER,
                       Roles.get_choice(Roles.TEACHER).permissions)
role_registry.register(Roles.GRADUATE,
                       Roles.get_choice(Roles.GRADUATE).permissions)
role_registry.register(Roles.VOLUNTEER,
                       Roles.get_choice(Roles.VOLUNTEER).permissions)
role_registry.register(Roles.CURATOR,
                       Roles.get_choice(Roles.CURATOR).permissions)
role_registry.register(Roles.INVITED,
                       Roles.get_choice(Roles.INVITED).permissions)
