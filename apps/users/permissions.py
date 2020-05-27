import rules

from auth.permissions import add_perm, Permission


@add_perm
class CreateCertificateOfParticipation(Permission):
    name = "users.create_certificate_of_participation"


@add_perm
class ViewCertificateOfParticipation(Permission):
    name = "users.view_certificate_of_participation"


@rules.predicate
def is_curator(user):
    return user.is_superuser and user.is_staff
