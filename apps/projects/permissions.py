import rules

from auth.permissions import add_perm, Permission
from projects.models import ReportComment


@add_perm
class ViewProjectsMenu(Permission):
    name = "learning.view_projects_menu"


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
