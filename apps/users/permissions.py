import rules


@rules.predicate
def is_curator(user):
    return user.is_superuser and user.is_staff
