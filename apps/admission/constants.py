from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, ChoiceItem

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
