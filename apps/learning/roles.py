from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

from auth.permissions import Role
from auth.registry import role_registry


from courses.permissions import ChangeMetaCourse, ViewCourseContacts, \
    ViewCourseAssignments
from .permissions import CreateAssignmentComment, \
    CreateAssignmentCommentTeacher, CreateAssignmentCommentStudent, \
    ViewStudyMenu, ViewCourseNews, ViewCourseReviews, ViewOwnEnrollments, \
    ViewOwnAssignments, ViewOwnAssignment, ViewCourses, ViewSchedule, ViewFAQ, \
    ViewLibrary, ViewInternships, EnrollInCourse, EnrollInCourseByInvitation, \
    LeaveCourse, ViewTeachingMenu, ViewOwnGradebook, ViewGradebook, \
    ViewStudentAssignment, ViewRelatedStudentAssignment, EditStudentAssignment, \
    EditOwnStudentAssignment


# TODO: Add description of each role
class Roles(DjangoChoices):
    STUDENT = C(1, _('Student'), permissions=(
        ViewStudyMenu,
        ViewCourseContacts,
        ViewCourseAssignments,
        ViewCourseNews,
        ViewCourseReviews,
        ViewOwnEnrollments,
        ViewOwnAssignments,
        ViewOwnAssignment,
        CreateAssignmentCommentStudent,
        ViewCourses,
        ViewSchedule,
        ViewFAQ,
        ViewLibrary,
        ViewInternships,
        EnrollInCourse,
        EnrollInCourseByInvitation,
        LeaveCourse,
    ))
    TEACHER = C(2, _('Teacher'), permissions=(
        ViewTeachingMenu,
        ViewCourseContacts,
        ViewCourseAssignments,
        ViewRelatedStudentAssignment,
        EditOwnStudentAssignment,
        ViewCourseNews,
        CreateAssignmentCommentTeacher,
        ViewOwnGradebook,
    ))
    GRADUATE = C(3, _('Graduate'), permissions=(
        ViewOwnEnrollments,
        ViewOwnAssignment,
    ))
    VOLUNTEER = C(4, _('Volunteer'), permissions=(
        ViewStudyMenu,
        ViewCourseContacts,
        ViewCourseAssignments,
        ViewCourseNews,
        ViewCourseReviews,
        ViewOwnEnrollments,
        ViewOwnAssignments,
        ViewOwnAssignment,
        CreateAssignmentCommentStudent,
        ViewCourses,
        ViewSchedule,
        ViewFAQ,
        ViewLibrary,
        ViewInternships,
        EnrollInCourse,
        EnrollInCourseByInvitation,
        LeaveCourse,
    ))
    CURATOR = C(5, _('Curator'), permissions=(
        ChangeMetaCourse,
        ViewCourseContacts,
        ViewCourseAssignments,
        ViewStudentAssignment,
        EditStudentAssignment,
        ViewCourseNews,
        ViewCourseReviews,
        ViewLibrary,
        CreateAssignmentCommentTeacher,
        ViewGradebook,
        CreateAssignmentComment,
    ))
    INVITED = C(11, _('Invited User'), permissions=(
        ViewStudyMenu,
        ViewCourseContacts,
        ViewCourseAssignments,
        ViewCourseNews,
        ViewCourseReviews,
        ViewOwnEnrollments,
        ViewOwnAssignments,
        ViewOwnAssignment,
        CreateAssignmentCommentStudent,
        ViewCourses,
        ViewSchedule,
        ViewFAQ,
        ViewLibrary,
        ViewInternships,
        EnrollInCourseByInvitation,
        LeaveCourse,
    ))


for code, name in Roles.choices:
    role_registry.register(Role(code=code, name=name,
                                permissions=Roles.get_choice(code).permissions))

# Add relations
teacher_role = role_registry[Roles.TEACHER]
teacher_role.add_relation(CreateAssignmentComment, CreateAssignmentCommentTeacher)
teacher_role.add_relation(ViewStudentAssignment, ViewRelatedStudentAssignment)
teacher_role.add_relation(EditStudentAssignment, EditOwnStudentAssignment)

student_role = role_registry[Roles.STUDENT]
student_role.add_relation(CreateAssignmentComment, CreateAssignmentCommentStudent)
