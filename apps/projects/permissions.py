import rules

from auth.permissions import add_perm
from projects.models import ReportComment


@rules.predicate
def update_report_comment(user, comment: ReportComment):
    return not comment.is_stale_for_editing and comment.author_id == user.pk


add_perm("learning.view_projects_menu")
add_perm("projects.change_own_reportcomment", update_report_comment)
add_perm("projects.change_reportcomment")
