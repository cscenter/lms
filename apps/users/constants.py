from djchoices import C, DjangoChoices

from django.utils.translation import gettext_lazy as _

BASE_THUMBNAIL_WIDTH = 176
BASE_THUMBNAIL_HEIGHT = 246


class GenderTypes(DjangoChoices):
    MALE = C('M', _('Male'))
    FEMALE = C('F', _('Female'))
    OTHER = C('o', _('Other/Prefer Not to Say'))


class ThumbnailSizes(DjangoChoices):
    """
    Base image aspect ratio is `5:7`.
    """
    BASE = C(f'{BASE_THUMBNAIL_WIDTH}x{BASE_THUMBNAIL_HEIGHT}')
    BASE_PRINT = C('250x350')
    SQUARE = C('150x150')
    SQUARE_SMALL = C('60x60')
    # FIXME: replace?
    INTERVIEW_LIST = C('100x100')
    # On center site only
    TEACHER_LIST = C("220x308")
    GRADUATE = C("344x482")


# FIXME: remove after deep refactoring:
#  1. Create service method `assign_role(user)` that must validate role id (it's impossible to use role registry as a source for the UserGroup.role choices')
#  2. Use this method to assign permission roles in the admin. (`auth.registry.role_registry` should be used for the admin form)
#  3. For backward compatibility it's better to change role id type to string
#  (after removing Role from the registry it's impossible to figure out what surrogate key means)
class Roles(DjangoChoices):
    STUDENT = C(1, _('Student'))
    TEACHER = C(2, _('Teacher'))
    GRADUATE = C(3, _('Graduate'))
    VOLUNTEER = C(4, _('Co-worker'))
    CURATOR = C(5, _('Curator'))
    INTERVIEWER = C(7, _('Interviewer [Admission]'))
    PROJECT_REVIEWER = C(9, _('Project reviewer'))
    CURATOR_PROJECTS = C(10, _('Curator of projects'))
    INVITED = C(11, _('Invited User'))
    SERVICE_USER = C(12, _("Service User"))
    PARTNER = C(13, _("Master's Degree Student"))


student_permission_roles = {Roles.INVITED, Roles.VOLUNTEER, Roles.PARTNER, Roles.STUDENT}


class SHADCourseGradeTypes(DjangoChoices):
    NOT_GRADED = C('not_graded', _("Not graded"))
    UNSATISFACTORY = C('unsatisfactory', _("SHADCourseGrade|Unsatisfactory"))
    CREDIT = C('pass', _("SHADCourseGrade|Pass"))
    GOOD = C('good', _("Good"))
    EXCELLENT = C('excellent', _("Excellent"))

    satisfactory_grades = {CREDIT.value, GOOD.value, EXCELLENT.value}

class ConsentTypes(DjangoChoices):
    LMS = C('lms', _("Yandex School of Data Analysis LMS terms of use"))
    OFFER = C('offer', _("Offer for the provision of additional professional education services"))
    TICKETS = C('tickets', _("Buying tickets, making reservations, obtaining permits to visit the countries of arrival"))
    
    regular_student_consents = {LMS.value, OFFER.value, TICKETS.value}
    invited_student_consents = {LMS.value, OFFER.value}


class TShirtSizeTypes(DjangoChoices):
    XXS = C('XXS')
    XS = C('XS')
    S = C('S')
    M = C('M')
    L = C('L')
    XL = C('XL')
    XXL = C('XXL')
    XXXL = C('XXXL')
