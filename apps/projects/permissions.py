import rules

from auth.permissions import add_perm, Permission
from projects.models import ReportComment, ProjectStudent, Report


@add_perm
class ViewProjectsMenu(Permission):
    name = "learning.view_projects_menu"


@add_perm
class ViewProjects(Permission):
    name = "projects.view_projects"


@add_perm
class ViewOwnProjects(Permission):
    name = "projects.view_own_projects"

    @staticmethod
    @rules.predicate
    def rule(user, project_student: ProjectStudent):
        return project_student.student_id == user.pk


@add_perm
class UpdateReportComment(Permission):
    name = "projects.change_reportcomment"


@add_perm
class UpdateOwnReportComment(Permission):
    name = "projects.change_own_reportcomment"

    @staticmethod
    @rules.predicate
    def rule(user, comment: ReportComment):
        return not comment.is_stale_for_editing and comment.author_id == user.pk


@add_perm
class ViewReportAttachment(Permission):
    name = "projects.view_report_attachment"


@add_perm
class ViewReportAttachmentAsLearner(Permission):
    name = "projects.view_own_report_attachment"

    @staticmethod
    @rules.predicate
    def rule(user, report: Report):
        if report.project_student.project.is_canceled:
            return False
        return user.pk == report.project_student.student_id


@add_perm
class ViewReportAttachmentAsReviewer(Permission):
    name = "projects.view_related_report_attachment"

    @staticmethod
    @rules.predicate
    def rule(user, report: Report):
        return user in report.project_student.project.reviewers.all()


@add_perm
class ViewReportCommentAttachment(Permission):
    name = "projects.view_report_comment_attachment"


@add_perm
class ViewReportCommentAttachmentAsLearner(Permission):
    name = "projects.view_own_report_comment_attachment"

    @staticmethod
    @rules.predicate
    def rule(user, report_comment: ReportComment):
        return report_comment.author_id == user.pk


@add_perm
class ViewReportCommentAttachmentAsReviewer(Permission):
    name = "projects.view_related_report_comment_attachment"

    @staticmethod
    @rules.predicate
    def rule(user, report_comment: ReportComment):
        project = report_comment.report.project_student.project
        return user in project.reviewers.all()
