from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

from auth.permissions import Role
from auth.registry import role_registry

from courses.permissions import ChangeMetaCourse, ViewCourseContacts, \
    ViewCourseAssignments, CreateAssignment, CreateOwnAssignment, \
    EditCourseClass, EditOwnCourseClass, DeleteOwnCourseClass, \
    DeleteCourseClass, EditAssignment, EditOwnAssignment, \
    ViewCourseClassMaterials, ViewAssignment, ViewOwnAssignment
from users.permissions import CreateCertificateOfParticipation, \
    ViewCertificateOfParticipation
from .permissions import CreateAssignmentComment, \
    CreateAssignmentCommentAsTeacher, CreateAssignmentCommentAsLearner, \
    ViewStudyMenu, ViewCourseNews, ViewCourseReviews, ViewOwnEnrollments, \
    ViewOwnStudentAssignments, ViewOwnStudentAssignment, ViewCourses, \
    ViewSchedule, ViewFAQ, \
    ViewLibrary, EnrollInCourse, EnrollInCourseByInvitation, \
    LeaveCourse, ViewTeachingMenu, ViewOwnGradebook, ViewGradebook, \
    ViewStudentAssignment, ViewRelatedStudentAssignment, EditStudentAssignment, \
    EditOwnStudentAssignment, ViewEnrollments, ViewRelatedEnrollments, \
    EditOwnAssignmentExecutionTime, ViewStudentAssignmentList, \
    ViewAssignmentCommentAttachment, ViewAssignmentCommentAttachmentAsLearner, \
    ViewAssignmentCommentAttachmentAsTeacher, ViewAssignmentAttachment, \
    ViewAssignmentAttachmentAsLearner, ViewAssignmentAttachmentAsTeacher
from info_blocks.permissions import ViewInternships


# TODO: Add description to each role
class Roles(DjangoChoices):
    CURATOR = C(5, _('Curator'), priority=0, permissions=(
        CreateCertificateOfParticipation,
        ViewCertificateOfParticipation,
        ChangeMetaCourse,
        CreateAssignment,
        EditAssignment,
        ViewAssignment,
        ViewCourseContacts,
        ViewCourseAssignments,
        ViewStudentAssignment,
        ViewStudentAssignmentList,
        EditStudentAssignment,
        EditCourseClass,
        DeleteCourseClass,
        ViewCourseNews,
        ViewCourseReviews,
        ViewLibrary,
        ViewEnrollments,
        CreateAssignmentCommentAsTeacher,
        ViewGradebook,
        CreateAssignmentComment,
        ViewAssignmentAttachment,
        ViewAssignmentCommentAttachment,
    ))
    STUDENT = C(1, _('Student'), priority=50, permissions=(
        ViewStudyMenu,
        ViewCourseContacts,
        ViewCourseAssignments,
        ViewCourseNews,
        ViewCourseReviews,
        ViewOwnEnrollments,
        ViewOwnStudentAssignments,
        ViewOwnStudentAssignment,
        ViewAssignmentAttachmentAsLearner,
        CreateAssignmentCommentAsLearner,
        ViewAssignmentCommentAttachmentAsLearner,
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
    VOLUNTEER = C(4, _('Co-worker'), priority=50,
                  permissions=STUDENT.permissions)
    INVITED = C(11, _('Invited User'), permissions=(
        ViewStudyMenu,
        ViewCourseContacts,
        ViewCourseAssignments,
        ViewCourseNews,
        ViewCourseReviews,
        ViewOwnEnrollments,
        ViewOwnStudentAssignments,
        ViewOwnStudentAssignment,
        ViewAssignmentAttachmentAsLearner,
        CreateAssignmentCommentAsLearner,
        ViewAssignmentCommentAttachmentAsLearner,
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
        ViewOwnStudentAssignment,
        ViewAssignmentAttachmentAsLearner,
        ViewAssignmentCommentAttachmentAsLearner,
    ))
    TEACHER = C(2, _('Teacher'), priority=30, permissions=(
        ViewTeachingMenu,
        ViewCourseContacts,
        ViewCourseNews,
        CreateOwnAssignment,
        EditOwnAssignment,
        ViewOwnAssignment,
        ViewCourseAssignments,
        ViewRelatedStudentAssignment,
        ViewStudentAssignmentList,
        EditOwnStudentAssignment,
        EditOwnCourseClass,
        DeleteOwnCourseClass,
        ViewRelatedEnrollments,
        ViewAssignmentAttachmentAsTeacher,
        CreateAssignmentCommentAsTeacher,
        ViewAssignmentCommentAttachmentAsTeacher,
        ViewOwnGradebook,
    ))


for code, name in Roles.choices:
    choice = Roles.get_choice(code)
    role = Role(code=code, name=name,
                priority=getattr(choice, 'priority', 100),
                permissions=choice.permissions)
    role_registry.register(role)

# Add relations
teacher_role = role_registry[Roles.TEACHER]
teacher_role.add_relation(ViewAssignmentAttachment,
                          ViewAssignmentAttachmentAsTeacher)
teacher_role.add_relation(CreateAssignmentComment,
                          CreateAssignmentCommentAsTeacher)
teacher_role.add_relation(ViewAssignmentCommentAttachment,
                          ViewAssignmentCommentAttachmentAsTeacher)
teacher_role.add_relation(ViewStudentAssignment, ViewRelatedStudentAssignment)
teacher_role.add_relation(EditStudentAssignment, EditOwnStudentAssignment)
teacher_role.add_relation(EditCourseClass, EditOwnCourseClass)
teacher_role.add_relation(DeleteCourseClass, DeleteOwnCourseClass)
teacher_role.add_relation(CreateAssignment, CreateOwnAssignment)
teacher_role.add_relation(EditAssignment, EditOwnAssignment)
teacher_role.add_relation(ViewAssignment, ViewOwnAssignment)
teacher_role.add_relation(ViewEnrollments, ViewRelatedEnrollments)

for role in (Roles.STUDENT, Roles.VOLUNTEER):
    student_role = role_registry[role]
    student_role.add_relation(ViewAssignmentAttachment,
                              ViewAssignmentAttachmentAsLearner)
    student_role.add_relation(CreateAssignmentComment,
                              CreateAssignmentCommentAsLearner)
    student_role.add_relation(ViewAssignmentCommentAttachment,
                              ViewAssignmentCommentAttachmentAsLearner)

default_role = role_registry.default_role
default_role.add_permission(ViewCourseClassMaterials)
