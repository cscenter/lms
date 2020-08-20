from django.utils.translation import gettext_lazy as _
from djchoices import DjangoChoices, C

REPORTING_NOTIFY_BEFORE_START = 3  # days
REPORTING_NOTIFY_BEFORE_DEADLINE = 1  # days

EDITING_REPORT_COMMENT_AVAIL = 600  # seconds


class ProjectTypes(DjangoChoices):
    practice = C('practice', _("StudentProject|Practice"))
    research = C('research', _("StudentProject|Research"))


class ProjectGradeTypes(DjangoChoices):
    """
    Used as grade choices for the ProjectStudent model.
    """
    NOT_GRADED = C('not_graded', _("ProjectGradeTypes|Not graded"))
    UNSATISFACTORY = C('unsatisfactory', _("ProjectGradeTypes|Unsatisfactory"))
    CREDIT = C('pass', _("ProjectGradeTypes|Pass"))
    GOOD = C('good', _("ProjectGradeTypes|Good"))
    EXCELLENT = C('excellent', _("ProjectGradeTypes|Excellent"))

    satisfactory_grades = {CREDIT.value, GOOD.value, EXCELLENT.value}