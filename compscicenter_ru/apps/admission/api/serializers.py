from django.conf import settings
from django.core.validators import validate_integer
from django.utils import formats
from rest_framework import serializers
from rest_framework.fields import empty, TimeField
from rest_framework.validators import UniqueTogetherValidator

from admission.constants import WHERE_DID_YOU_LEARN
from admission.models import Applicant, Campaign, University, InterviewSlot
from admission.tasks import register_in_yandex_contest


class ActiveCampaignField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        if self.queryset:
            return self.queryset.all()
        return Campaign.get_active()


class ApplicantSerializer(serializers.ModelSerializer):
    where_did_you_learn = serializers.MultipleChoiceField(
        WHERE_DID_YOU_LEARN,
        allow_empty=False)
    preferred_study_programs = serializers.MultipleChoiceField(
        Applicant.STUDY_PROGRAMS,
        required=False,
        error_messages={
            'empty': 'Выберите интересующие вас направления обучения'
        }
    )
    campaign = ActiveCampaignField(
        label='Отделение',
        error_messages={
            'does_not_exist': 'Приемная кампания окончена либо не существует',
            'incorrect_type': 'Некорректное значение идентификатора кампании'
        })
    # Note: This field is marked as required on a form level only since
    # curators could edit applicant info in admin without knowing all details.
    has_job = serializers.BooleanField(label='Вы сейчас работаете?')
    # FIXME: Replace with hidden field since real value stores in session
    yandex_login = serializers.CharField(max_length=80)

    class Meta:
        model = Applicant
        fields = (
            # Personal info
            "surname", "first_name", "patronymic",
            "email", "phone",
            # Accounts
            "stepic_id", "github_login", "yandex_login",
            # Education
            "university", "university_other", "faculty", "course",
            # Work
            "has_job", "workplace", "position",
            "experience", "online_education_experience",
            # CSC
            "campaign",
            "living_place",
            "preferred_study_programs",
            "preferred_study_programs_dm_note",
            "preferred_study_programs_cs_note",
            "preferred_study_programs_se_note",
            "motivation",
            "probability",
            "additional_info",
            # Source
            "where_did_you_learn", "where_did_you_learn_other",
        )
        extra_kwargs = {
            'university': {
                'error_messages': {
                    'does_not_exist': 'Университет не найден среди допустимых значений'
                }
            },
        }
        validators = [
            UniqueTogetherValidator(
                queryset=Applicant.objects.all(),
                fields=('email', 'campaign'),
                message="Если вы уже зарегистрировали анкету на "
                        "указанный email и хотите внести изменения, "
                        "напишите на info@compscicenter.ru с этой почты.")
        ]

    def __init__(self, instance=None, data=empty, **kwargs):
        if data is not empty and data:
            if "university_other" in data:
                # Make university optional cause its value should be empty in
                # case when `university_other` value provided. Set value
                # later in `.validate` method.
                self.fields["university"].required = False
            if "campaign" in data:
                try:
                    # This logic adds one additional DB hit, but
                    # improves validation since we need dynamically set
                    # `required` logic for some fields
                    campaign_id = int(data['campaign'])
                    campaign = (self.fields['campaign']
                                .get_queryset()
                                .get(pk=campaign_id))
                    if campaign.branch.city_id:
                        field = self.fields["preferred_study_programs"]
                        field.required = True
                        field.allow_empty = False
                    elif not data.get("living_place"):
                        self.fields["living_place"].required = True
                except (ValueError, Campaign.DoesNotExist):
                    self.fields['campaign'].queryset = Campaign.objects.none()
        super().__init__(instance, data, **kwargs)

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        if instance.pk:
            register_in_yandex_contest.delay(instance.pk,
                                             settings.LANGUAGE_CODE)
        return instance

    def validate(self, attrs):
        campaign = attrs['campaign']
        if not attrs.get('has_job'):
            to_delete = ('workplace', 'position')
            for attr in to_delete:
                if attr in attrs:
                    del attrs[attr]
        if attrs.get('university_other'):
            university, created = University.objects.get_or_create(
                abbr="other", branch_id=None,
                defaults={"name": "Другое"})
            attrs['university'] = university
        # TODO: if where_did_you_learn.other selected, where_did_you_learn_other should be provided?
        return attrs

    def validate_stepic_id(self, value):
        return value.rsplit("/", maxsplit=1)[-1]

    def validate_github_login(self, value):
        return value.rsplit("/", maxsplit=1)[-1]


class InterviewSlotSerializer(serializers.ModelSerializer):
    start_at = TimeField(format="%H:%M", input_formats=None)
    stream = serializers.SerializerMethodField()

    class Meta:
        model = InterviewSlot
        fields = ("id", "start_at", "interview_id", "stream")

    def get_stream(self, obj):
        return formats.date_format(obj.stream.date, "SHORT_DATE_FORMAT")
