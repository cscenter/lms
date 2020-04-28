from auth.permissions import add_perm, Permission


@add_perm
class ViewAdmissionMenu(Permission):
    name = "learning.view_admission_menu"
