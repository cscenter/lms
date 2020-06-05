from auth.permissions import add_perm, Permission
from learning.permissions import has_active_status


@add_perm
class ViewInternships(Permission):
    name = "study.view_internships"
    rule = has_active_status
