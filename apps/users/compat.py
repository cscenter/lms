from django.contrib.sites.models import Site

from learning.models import GraduateProfile
from users.models import User


# FIXME: ProjectPublicationAuthor must reference StudentProfile instead of User model, then use `users.services.get_graduate_profile` method
# FIXME: Doesn't work well if user has more than 1 graduate profile on site
def get_graduate_profile(user: User, site: Site):
    return (GraduateProfile.active
            .filter(student_profile__user=user,
                    student_profile__branch__site=site)
            .order_by('pk')
            .first())
