from djchoices import C, ChoiceItem, DjangoChoices

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

WHERE_DID_YOU_LEARN = (
    ('uni', 'плакат в университете'),
    ('group', 'tg-канал / группа в университете'),
    ('post', 'пост в VK / tg-канале'),
    ('mailing', 'рассылка по почте'),
    ('community', 'от студента / выпускника / преподавателя ШАДа'),
    ('ambassador', 'от амбассадора Yandex U-Team'),
    ('friends', 'от друзей'),
    ('bloger', 'от блогера'),
    ('other', 'другое')
)

INVITATION_EXPIRED_IN_HOURS = 27
EMAIL_VERIFICATION_CODE_TEMPLATE = "emails/admission/email_verification_code.txt"


class ApplicantStatuses(DjangoChoices):
    REJECTED_BY_FORM_CHECK = C("rejected_form_check", _("Rejected by form check"))
    GOLDEN_TICKET = C("golden_ticket", _("Golden ticket from the previous year"))
    REJECTED_BY_CHEATING = C("rejected_cheating", _("Cheating"))
    REJECTED_BY_TEST = C("rejected_test", _("Rejected by test"))
    PERMIT_TO_OLYMPIAD = C("permit_to_olympiad", _("Permitted to the olympiad"))
    PERMIT_TO_EXAM = C("permit_to_exam", _("Permitted to the exam"))
    PASSED_OLYMPIAD = C("passed_olympiad", _("Passed the olympiad"))
    FAILED_OLYMPIAD = C("failed_olympiad", _("Failed the olympiad, will write the exam"))
    REJECTED_BY_EXAM_CHEATING = C("reject_exam_cheater", _("Rejected by exam cheating"))
    REJECTED_BY_EXAM = C("rejected_exam", _("Rejected by exam"))
    PASSED_EXAM = C("passed_exam", _("Passed the exam"))
    REJECTED_BY_INTERVIEW = C("rejected_interview", _("Rejected by interview"))
    REJECTED_BY_INTERVIEW_WITH_BONUS = C(
        "rejected_with_bonus", _("Rejected by interview. Offered a bonus")
    )
    ACCEPT = C("accept", _("Accept"))
    ACCEPT_IF = C("accept_if", _("Accept with condition"))
    THEY_REFUSED = C("they_refused", _("He or she refused"))
    PERMIT_TO_INTENSIVE = C("permit_to_intensive", _("Permitted to the intensive"))
    PENDING = C("pending", _("Pending"))
    REJECTED_BY_INTENSIVE = C("rejected_intensive", _("Rejected by intensive"))
    REJECTED_BY_INTENSIVE_WITH_BONUS = C("rejected_intensive_bonus", _("Rejected by intensive. Offered a bonus"))
    ACCEPT_PAID = C("accept_paid", _("Accept on paid"))

    ENTERING_MASTERS_PRESELECT = C("entering_masters_preselect", _("Entering the master's program (pre-selection)"))
    PASSED_EXAM_PRESELECT = C("passed_exam_preselect", _("Passed the exam (pre-selection)"))
    REJECTED_BY_EXAM_PRESELECT =C("rejected_exam_preselect", _("Rejected by exam (pre-selection)"))
    RECOMMENDED_MASTERS_PRESELECT = C("recommended_masters_preselect", _("Recommended for the master's program (pre-selection)"))
    REJECTED_BY_INTERVIEW_PRESELECT = C("rejected_interview_preselect", _("Rejected by interview (pre-selection)"))
    ACCEPTED_MASTERS_PRESELECT = C("accepted_masters_preselect", _("Accepted for the master's program (pre-selection)"))
    REJECTED_MASTERS_PRESELECT = C("rejected_masters_preselect", _("Refused to enroll the master's program (pre-selection)"))


    # Applicants whose next step is interview.
    # Modern equivalent of INTERVIEW_TOBE_SCHEDULED
    RIGHT_BEFORE_INTERVIEW = {
        PASSED_EXAM.value,
        GOLDEN_TICKET.value,
        PASSED_OLYMPIAD.value
    }

    # Applicants who have reached the interview stage
    RESULTS_STATUSES = {
        *RIGHT_BEFORE_INTERVIEW,
        REJECTED_BY_INTERVIEW.value,
        REJECTED_BY_INTERVIEW_WITH_BONUS.value,
        ACCEPT_PAID.value,
        ACCEPT.value,
        ACCEPT_IF.value,
        THEY_REFUSED.value,
    }

    @classmethod
    @property
    def RIGHT_BEFORE_INTERVIEW_DISPLAY(self):
        return [self.get_choice(value).label for value in self.RIGHT_BEFORE_INTERVIEW]


class ContestTypes(DjangoChoices):
    TEST = C(1, _("Testing"))
    EXAM = C(2, _("Exam"))
    OLYMPIAD = C(3, _("Olympiad"))


class ChallengeStatuses(DjangoChoices):
    NEW = ChoiceItem("new", _("Not registered in the contest"))
    # Results could be imported from a contest
    REGISTERED = ChoiceItem("registered", _("Syncing with a contest"))
    MANUAL = ChoiceItem("manual", _("Manual score input"))


class InterviewFormats(DjangoChoices):
    OFFLINE = ChoiceItem("offline", _("Offline"))
    ONLINE = ChoiceItem("online", _("Online"))

class ApplicantInterviewFormats(DjangoChoices):
    OFFLINE = ChoiceItem("offline", _("Offline"))
    ONLINE = ChoiceItem("online", _("Online"))
    ANY = ChoiceItem("any", _("Any"))


class InterviewSections(DjangoChoices):
    ALL_IN_ONE = C("all_in_1", pgettext_lazy("section", "Common Section"))
    MATH = C("math", pgettext_lazy("section", "Math"))
    PROGRAMMING = C("code", pgettext_lazy("section", "Code"))
    MATH_PROGRAMMING = C("math_code", pgettext_lazy("section", "Math and code"))
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

class MIPTTracks(DjangoChoices):
    BASIC = C("basic", _('Basiс track'))
    ADVANCED = C("advanced", _('Advanced track'))

SESSION_CONFIRMATION_CODE_KEY = "admission_confirmation_code"

class UTMNames(DjangoChoices):
    SOURCE = ChoiceItem("utm_source")
    MEDIUM = ChoiceItem("utm_medium")
    CAMPAIGN = ChoiceItem("utm_campaign")
    TERM = ChoiceItem("utm_term")
    CONTENT = ChoiceItem("utm_content")
