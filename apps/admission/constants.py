from djchoices import C, ChoiceItem, DjangoChoices

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

WHERE_DID_YOU_LEARN = (
    ('uni', 'плакат в университете'),
    ('social_net', 'пост в социальных сетях'),
    ('ambassador', 'от амбассадора Yandex U-Team'),
    ('friends', 'от друзей'),
    ('other', 'другое')
)

INVITATION_EXPIRED_IN_HOURS = 27
EMAIL_VERIFICATION_CODE_TEMPLATE = "emails/admission/email_verification_code.txt"


class ApplicantStatuses(DjangoChoices):
    REJECTED_BY_TEST = C("rejected_test", _("Rejected by test"))
    PERMIT_TO_EXAM = C("permit_to_exam", _("Permitted to the exam"))
    REJECTED_BY_EXAM = C("rejected_exam", _("Rejected by exam"))
    REJECTED_BY_EXAM_CHEATING = C("reject_exam_cheater", _("Rejected by exam cheating"))
    REJECTED_BY_CHEATING = C("rejected_cheating", _("Cheating"))
    PENDING = C("pending", _("Pending"))
    # TODO: rename interview codes here and in DB.
    INTERVIEW_TOBE_SCHEDULED = C(
        "interview_phase", _("Can be interviewed")
    )  # permitted to interview
    INTERVIEW_SCHEDULED = C("interview_assigned", _("Interview assigned"))
    INTERVIEW_COMPLETED = C("interview_completed", _("Interview completed"))
    REJECTED_BY_INTERVIEW = C("rejected_interview", _("Rejected by interview"))
    REJECTED_BY_INTERVIEW_WITH_BONUS = C(
        "rejected_with_bonus", _("Rejected by interview. Offered a bonus")
    )
    ACCEPT_PAID = C("accept_paid", _("Accept on paid"))
    WAITING_FOR_PAYMENT = C("waiting_for_payment", _("Waiting for Payment"))
    ACCEPT = C("accept", _("Accept"))
    ACCEPT_IF = C("accept_if", _("Accept with condition"))
    VOLUNTEER = C("volunteer", _("Applicant|Volunteer"))
    THEY_REFUSED = C("they_refused", _("He or she refused"))

    # Participants who have reached the interview stage
    RESULTS_STATUSES = {
        INTERVIEW_TOBE_SCHEDULED.value,
        INTERVIEW_SCHEDULED.value,
        INTERVIEW_COMPLETED.value,
        REJECTED_BY_INTERVIEW.value,
        REJECTED_BY_INTERVIEW_WITH_BONUS.value,
        ACCEPT_PAID.value,
        WAITING_FOR_PAYMENT.value,
        ACCEPT.value,
        ACCEPT_IF.value,
        VOLUNTEER.value,
        THEY_REFUSED.value,
    }


class ContestTypes(DjangoChoices):
    TEST = C(1, _("Testing"))
    EXAM = C(2, _("Exam"))


class ChallengeStatuses(DjangoChoices):
    NEW = ChoiceItem("new", _("Not registered in the contest"))
    # Results could be imported from a contest
    REGISTERED = ChoiceItem("registered", _("Syncing with a contest"))
    MANUAL = ChoiceItem("manual", _("Manual score input"))


class InterviewFormats(DjangoChoices):
    OFFLINE = ChoiceItem("offline", _("Offline"))
    ONLINE = ChoiceItem("online", _("Online"))


class InterviewSections(DjangoChoices):
    ALL_IN_ONE = C("all_in_1", pgettext_lazy("section", "Common Section"))
    MATH = C("math", pgettext_lazy("section", "Math"))
    PROGRAMMING = C("code", pgettext_lazy("section", "Code"))
    MOTIVATION = C("mv", pgettext_lazy("section", "Motivation"))


class InterviewInvitationStatuses(DjangoChoices):
    # This status means applicant did not perform any action on this invitation
    NO_RESPONSE = C("created", _("No Response"))
    DECLINED = C("declined", _("Declined"))
    # TODO: auto-update status for expired invitation: rq task or in a lazy manner (but where?)
    # Note: explicit status for expired invitation is out of
    # sync with actual checking for expiration time
    EXPIRED = C("expired", _("Expired"))
    ACCEPTED = C("accepted", _("Accepted"))

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


class DefaultInterviewRatingSystem(DjangoChoices):
    MINUS_TWO = ChoiceItem(-2, "не брать ни сейчас, ни потом (-2)")
    MINUS_ONE = ChoiceItem(-1, "не брать сейчас (-1)")
    ZERO = ChoiceItem(0, "нейтрально (0)")
    PLUS_ONE = ChoiceItem(1, "можно взять (1)")
    PLUS_TWO = ChoiceItem(2, "точно нужно взять (2)")


class YandexDataSchoolInterviewRatingSystem(DjangoChoices):
    ONE = ChoiceItem(1, "не брать ни сейчас, ни потом (1)")
    TWO = ChoiceItem(2, "не брать сейчас (2)")
    THREE = ChoiceItem(3, "нейтрально (3)")
    FOUR = ChoiceItem(4, "можно взять (4)")
    FIVE = ChoiceItem(5, "точно нужно взять (5)")

class DiplomaDegrees(DjangoChoices):
    BACHELOR = C("1", _('bachelor'))
    SPECIALITY = C("2", _('speciality'))
    MAGISTRACY = C("3", _('magistracy'))
    POSTGRADUATE = C("4", _('postgraduate'))
    SECONDARY_PROFESSIONAL = C("5", _('secondary professional'))

class HasDiplomaStatuses(DjangoChoices):
    YES = C("yes", _('yes'))
    IN_PROCESS = C("in_process", _('in process of getting degree'))
    NO = C("no", _('no'))

SESSION_CONFIRMATION_CODE_KEY = "admission_confirmation_code"
