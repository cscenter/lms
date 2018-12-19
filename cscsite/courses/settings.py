from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C


class SemesterTypes(DjangoChoices):
    """
    For ordering use the first term in a year as starting point.
    Term order values must be consecutive numbers.
    """
    SPRING = C('spring', _("spring"), order=1)
    SUMMER = C('summer', _("summer"), order=2)
    AUTUMN = C('autumn', _("autumn"), order=3)


class ClassTypes(DjangoChoices):
    LECTURE = C('lecture', _("Lecture"))
    SEMINAR = C('seminar', _("Seminar"))


# Helps to sort terms in chronological order
# FIXME: move to Semester model?
TERMS_INDEX_START = 1
