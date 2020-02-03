from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

from auth.permissions import Role
from auth.registry import role_registry

from courses.permissions import ChangeMetaCourse, ViewCourseContacts, \
    ViewCourseAssignments, CreateAssignment, CreateOwnAssignment, \
    EditCourseClass, EditOwnCourseClass, DeleteOwnCourseClass, \
    DeleteCourseClass, EditAssignment, EditOwnAssignment
from .permissions import CreateAssignmentComment, \
    CreateAssignmentCommentTeacher, CreateAssignmentCommentStudent, \
    ViewStudyMenu, ViewCourseNews, ViewCourseReviews, ViewOwnEnrollments, \
    ViewOwnAssignments, ViewOwnAssignment, ViewCourses, ViewSchedule, ViewFAQ, \
    ViewLibrary, ViewInternships, EnrollInCourse, EnrollInCourseByInvitation, \
    LeaveCourse, ViewTeachingMenu, ViewOwnGradebook, ViewGradebook, \
    ViewStudentAssignment, ViewRelatedStudentAssignment, EditStudentAssignment, \
    EditOwnStudentAssignment, ViewEnrollments, ViewRelatedEnrollments, \
    EditOwnAssignmentExecutionTime


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
        EditOwnAssignmentExecutionTime,
        ViewCourses,
        ViewSchedule,
        ViewFAQ,
        ViewLibrary,
        ViewInternships,
        EnrollInCourse,
        EnrollInCourseByInvitation,
        LeaveCourse,
    ))
    # FIXME: copy permissions from student role, there are identical
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
        EditOwnAssignmentExecutionTime,
        ViewCourses,
        ViewSchedule,
        ViewFAQ,
        ViewLibrary,
        ViewInternships,
        EnrollInCourse,
        EnrollInCourseByInvitation,
        LeaveCourse,
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
    GRADUATE = C(3, _('Graduate'), permissions=(
        ViewOwnEnrollments,
        ViewOwnAssignment,
    ))
    TEACHER = C(2, _('Teacher'), permissions=(
        ViewTeachingMenu,
        ViewCourseContacts,
        ViewCourseNews,
        CreateOwnAssignment,
        EditOwnAssignment,
        ViewCourseAssignments,
        ViewRelatedStudentAssignment,
        EditOwnStudentAssignment,
        EditOwnCourseClass,
        DeleteOwnCourseClass,
        ViewRelatedEnrollments,
        CreateAssignmentCommentTeacher,
        ViewOwnGradebook,
    ))
    CURATOR = C(5, _('Curator'), permissions=(
        ChangeMetaCourse,
        CreateAssignment,
        EditAssignment,
        ViewCourseContacts,
        ViewCourseAssignments,
        ViewStudentAssignment,
        EditStudentAssignment,
        EditCourseClass,
        DeleteCourseClass,
        ViewCourseNews,
        ViewCourseReviews,
        ViewLibrary,
        ViewEnrollments,
        CreateAssignmentCommentTeacher,
        ViewGradebook,
        CreateAssignmentComment,
    ))


for code, name in Roles.choices:
    role_registry.register(Role(code=code, name=name,
                                permissions=Roles.get_choice(code).permissions))

# Add relations
teacher_role = role_registry[Roles.TEACHER]
teacher_role.add_relation(CreateAssignmentComment, CreateAssignmentCommentTeacher)
teacher_role.add_relation(ViewStudentAssignment, ViewRelatedStudentAssignment)
teacher_role.add_relation(EditStudentAssignment, EditOwnStudentAssignment)
teacher_role.add_relation(EditCourseClass, EditOwnCourseClass)
teacher_role.add_relation(DeleteCourseClass, DeleteOwnCourseClass)
teacher_role.add_relation(CreateAssignment, CreateOwnAssignment)
teacher_role.add_relation(EditAssignment, EditOwnAssignment)
teacher_role.add_relation(ViewEnrollments, ViewRelatedEnrollments)

student_role = role_registry[Roles.STUDENT]
student_role.add_relation(CreateAssignmentComment, CreateAssignmentCommentStudent)
