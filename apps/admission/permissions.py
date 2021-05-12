from auth.permissions import Permission, add_perm


@add_perm
class ViewAdmissionMenu(Permission):
    name = "learning.view_admission_menu"
