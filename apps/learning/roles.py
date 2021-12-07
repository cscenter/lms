from djchoices import C, DjangoChoices

from django.apps import apps
from django.utils.translation import gettext_lazy as _

from auth.permissions import Role
from auth.registry import role_registry
from courses.permissions import (
    ChangeMetaCourse, CreateAssignment, CreateOwnAssignment, DeleteCourseClass,
    DeleteOwnCourseClass, EditAssignment, EditCourseClass, EditOwnAssignment,
    EditOwnCourseClass, ViewAssignment, ViewCourse, ViewCourseAssignments,
    ViewCourseClassMaterials, ViewCourseContacts, ViewOwnAssignment, DeleteAssignment, DeleteOwnAssignment,
    DeleteAssignmentAttachment, DeleteAssignmentAttachmentAsTeacher
)
from info_blocks.permissions import ViewInternships
from users.permissions import (
    CreateCertificateOfParticipation, ViewAccountConnectedServiceProvider,
    ViewCertificateOfParticipation
)

from .permissions import (
    CreateAssignmentComment, CreateAssignmentCommentAsLearner,
    CreateAssignmentCommentAsTeacher, CreateAssignmentSolution,
    CreateOwnAssignmentSolution, CreateStudentGroup, CreateStudentGroupAsTeacher,
    DeleteStudentGroup, DeleteStudentGroupAsTeacher, DownloadAssignmentSolutions,
    EditGradebook, EditOwnAssignmentExecutionTime, EditOwnGradebook,
    EditOwnStudentAssignment, EditStudentAssignment, EnrollInCourse,
    EnrollInCourseByInvitation, LeaveCourse, UpdateStudentGroup,
    UpdateStudentGroupAsTeacher, ViewAssignmentAttachment,
    ViewAssignmentAttachmentAsLearner, ViewAssignmentAttachmentAsTeacher,
    ViewAssignmentCommentAttachment, ViewAssignmentCommentAttachmentAsLearner,
    ViewAssignmentCommentAttachmentAsTeacher, ViewCourseNews, ViewCourseReviews,
    ViewCourses, ViewEnrollments, ViewFAQ, ViewGradebook, ViewLibrary,
    ViewOwnEnrollments, ViewOwnGradebook, ViewOwnStudentAssignment,
    ViewOwnStudentAssignments, ViewRelatedEnrollments, ViewRelatedStudentAssignment,
    ViewSchedule, ViewStudentAssignment, ViewStudentAssignmentList, ViewStudentGroup,
    ViewStudentGroupAsTeacher, ViewStudyMenu, ViewTeachingMenu
)


# TODO: Add description to each role
class Roles(DjangoChoices):
    CURATOR = C(5, _('Curator'), priority=0, permissions=(
        ViewAccountConnectedServiceProvider,
        ViewCourse,
        CreateCertificateOfParticipation,
        ViewCertificateOfParticipation,
        ChangeMetaCourse,
        CreateAssignment,
        EditAssignment,
        ViewAssignment,
        DeleteAssignment,
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
        EditGradebook,
        CreateAssignmentComment,
        CreateAssignmentSolution,
        DownloadAssignmentSolutions,
        ViewAssignmentAttachment,
        DeleteAssignmentAttachment,
        ViewAssignmentCommentAttachment,
        ViewStudentGroup,
        UpdateStudentGroup,
        DeleteStudentGroup,
        CreateStudentGroup,
    ))
    STUDENT = C(1, _('Student'), priority=50, permissions=(
        ViewCourse,
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
        CreateOwnAssignmentSolution,
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
    PARTNER = C(13, _("Master's Degree Student"), priority=50,
                permissions=STUDENT.permissions)
    INVITED = C(11, _('Invited User'), permissions=(
        ViewCourse,
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
        CreateOwnAssignmentSolution,
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
        ViewCourse,
        ViewOwnEnrollments,
        ViewOwnStudentAssignment,
        ViewAssignmentAttachmentAsLearner,
        ViewAssignmentCommentAttachmentAsLearner,
    ))
    TEACHER = C(2, _('Teacher'), priority=30, permissions=(
        ViewCourse,
        ViewTeachingMenu,
        ViewCourseContacts,
        ViewCourseNews,
        CreateOwnAssignment,
        EditOwnAssignment,
        ViewOwnAssignment,
        DeleteOwnAssignment,
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
        DeleteAssignmentAttachmentAsTeacher,
        ViewOwnGradebook,
        EditOwnGradebook,
        ViewStudentGroupAsTeacher,
        UpdateStudentGroupAsTeacher,
        DeleteStudentGroupAsTeacher,
        CreateStudentGroupAsTeacher,
    ))


for code, name in Roles.choices:
    choice = Roles.get_choice(code)
    role = Role(id=code, code=code, description=name,
                priority=getattr(choice, 'priority', 100),
                permissions=choice.permissions)
    role_registry.register(role)

# Add relations
teacher_role = role_registry[Roles.TEACHER]
teacher_role.add_relation(ViewAssignmentAttachment,
                          ViewAssignmentAttachmentAsTeacher)
teacher_role.add_relation(DeleteAssignmentAttachment,
                          DeleteAssignmentAttachmentAsTeacher)
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
teacher_role.add_relation(DeleteAssignment, DeleteOwnAssignment)
teacher_role.add_relation(ViewEnrollments, ViewRelatedEnrollments)
teacher_role.add_relation(ViewGradebook, ViewOwnGradebook)
teacher_role.add_relation(EditGradebook, EditOwnGradebook)
teacher_role.add_relation(ViewStudentGroup, ViewStudentGroupAsTeacher)
teacher_role.add_relation(CreateStudentGroup, CreateStudentGroupAsTeacher)
teacher_role.add_relation(DeleteStudentGroup, DeleteStudentGroupAsTeacher)
teacher_role.add_relation(UpdateStudentGroup, UpdateStudentGroupAsTeacher)


for role in (Roles.STUDENT, Roles.VOLUNTEER, Roles.PARTNER, Roles.INVITED):
    student_role = role_registry[role]
    student_role.add_relation(ViewAssignmentAttachment,
                              ViewAssignmentAttachmentAsLearner)
    student_role.add_relation(CreateAssignmentComment,
                              CreateAssignmentCommentAsLearner)
    student_role.add_relation(CreateAssignmentSolution,
                              CreateOwnAssignmentSolution)
    student_role.add_relation(ViewAssignmentCommentAttachment,
                              ViewAssignmentCommentAttachmentAsLearner)

graduate_role = role_registry[Roles.GRADUATE]
graduate_role.add_relation(ViewAssignmentAttachment, ViewAssignmentAttachmentAsLearner)
graduate_role.add_relation(ViewAssignmentCommentAttachment, ViewAssignmentCommentAttachmentAsLearner)

anonymous_role = role_registry.anonymous_role
anonymous_role.add_permission(ViewCourseClassMaterials)


# TODO: Write util method to view all role permissions, register global roles
#  like student, teacher, curator with `core` (or `lms`) app, then move
#  code below to the `projects` app
if apps.is_installed('projects'):
    from projects.permissions import (
        ViewReportAttachment, ViewReportAttachmentAsLearner,
        ViewReportCommentAttachment, ViewReportCommentAttachmentAsLearner
    )

    curator_role = role_registry[Roles.CURATOR]
    curator_role.add_permission(ViewReportAttachment)
    curator_role.add_permission(ViewReportCommentAttachment)

    for role in (Roles.STUDENT, Roles.VOLUNTEER, Roles.PARTNER):
        student_role = role_registry[role]
        # Permissions
        student_role.add_permission(ViewReportAttachmentAsLearner)
        student_role.add_permission(ViewReportCommentAttachmentAsLearner)
        # Relations
        student_role.add_relation(ViewReportAttachment,
                                  ViewReportAttachmentAsLearner)
        student_role.add_relation(ViewReportCommentAttachment,
                                  ViewReportCommentAttachmentAsLearner)
