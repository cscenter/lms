from djchoices import C, ChoiceItem, DjangoChoices

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

WHERE_DID_YOU_LEARN = (
    ('uni', 'плакат в университете'),
    ('social_net', 'пост в социальных сетях'),
    ('friends', 'от друзей'),
    ('other', 'другое')
)

INVITATION_EXPIRED_IN_HOURS = 27

# Email templates
APPOINTMENT_INVITATION_TEMPLATE = "admission-interview-invitation"
INTERVIEW_REMINDER_TEMPLATE = "admission-interview-reminder"
INTERVIEW_FEEDBACK_TEMPLATE = "admission-interview-feedback"


class ChallengeStatuses(DjangoChoices):
    NEW = ChoiceItem('new', _("Not registered in the contest"))
    # Results could be imported from a contest
    REGISTERED = ChoiceItem('registered', _("Syncing with a contest"))
    MANUAL = ChoiceItem('manual', _("Manual score input"))


class InterviewFormats(DjangoChoices):
    OFFLINE = ChoiceItem('offline', _("Offline"))
    ONLINE = ChoiceItem('online', _("Online"))


class InterviewSections(DjangoChoices):
    ALL_IN_ONE = C('all_in_1', pgettext_lazy("section", "Common Section"))
    MATH = C('math', pgettext_lazy("section", "Math"))
    PROGRAMMING = C('code', pgettext_lazy("section", "Coding"))
    MOTIVATION = C('mv', pgettext_lazy("section", "Motivation"))


class InterviewInvitationStatuses(DjangoChoices):
    # This status means applicant did not perform any action on this invitation
    CREATED = C('created', _("No Response"))
    DECLINED = C('declined', _("Declined"))
    # TODO: auto-update status for expired invitation: rq task or in a lazy manner (but where?)
    # Note: explicit status for expired invitation is out of
    # sync with actual checking for expiration time
    EXPIRED = C('expired', _("Expired"))
    ACCEPTED = C('accepted', _("Accepted"))

    @classmethod
    def get_code(cls, value):
        if value == cls.DECLINED:
            return "danger"
        elif value == cls.EXPIRED:
            return "info"
        elif value == cls.ACCEPTED:
            return "success"
        else:
            return "default"


class ShadScaleComment(DjangoChoices):
    ONE = ChoiceItem(1, _("не брать ни сейчас, ни потом (1)"))
    TWO = ChoiceItem(2, _("не брать сейчас (2)"))
    THREE = ChoiceItem(3, _("нейтрально (3)"))
    FOUR = ChoiceItem(4, _("можно взять (4)"))
    FIVE = ChoiceItem(5, _("точно нужно взять (5)"))


class CscScaleComment(DjangoChoices):
    MINUS_TWO = ChoiceItem(-2, _("не брать ни сейчас, ни потом (-2)"))
    MINUS_ONE = ChoiceItem(-1, _("не брать сейчас (-1)"))
    ZERO = ChoiceItem(0, _("нейтрально (0)"))
    PLUS_ONE = ChoiceItem(1, _("можно взять (1)"))
    PLUS_TWO = ChoiceItem(2, _("точно нужно взять (2)"))
