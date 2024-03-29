from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.validators import UniqueTogetherValidator

from django.conf import settings

from admission.api.serializers import OpenRegistrationCampaignField
from admission.constants import WHERE_DID_YOU_LEARN
from admission.models import Applicant, Campaign
from admission.tasks import register_in_yandex_contest
from core.models import University


class ApplicationFormSerializer(serializers.ModelSerializer):
    where_did_you_learn = serializers.MultipleChoiceField(
        choices=WHERE_DID_YOU_LEARN,
        allow_empty=False)
    preferred_study_programs = serializers.MultipleChoiceField(
        choices=Applicant.STUDY_PROGRAMS,
        allow_empty=False,
        error_messages={
            'empty': 'Выберите интересующие вас направления обучения'
        }
    )
    preferred_study_programs_robotics_note = serializers.CharField(
        required=False,
        allow_blank=True,
        label='Какие направления применения роботов вы считаете наиболее перспективными?',
    )
    campaign = OpenRegistrationCampaignField(
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
            "last_name", "first_name", "patronymic",
            "email", "phone",
            # Accounts
            "stepic_id", "github_login", "yandex_login",
            # Education
            "university", "university_other", "faculty", "level_of_education",
            # Work
            "has_job", "workplace", "position",
            "experience", "online_education_experience",
            # CSC
            "campaign",
            "living_place",
            "preferred_study_programs",
            "preferred_study_programs_robotics_note",
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
        super().__init__(instance, data, **kwargs)
        self.fields["living_place"].required = True
        if data is not empty and data:
            if "university_other" in data:
                # Make university optional cause its value should be empty in
                # case when `university_other` value provided. Set value
                # later in `.validate` method.
                self.fields["university"].required = False

    def create(self, validated_data):
        data = {**validated_data}
        if "preferred_study_programs_robotics_note" in data:
            if data["preferred_study_programs_robotics_note"]:
                label = self.fields['preferred_study_programs_robotics_note'].label
                value = data.get('preferred_study_programs_robotics_note')
                data['preferred_study_program_notes'] = f"{label}\n{value}"
            del data["preferred_study_programs_robotics_note"]
        return super().create(data)

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        if instance.pk:
            # TODO: better to add transaction.on_commit
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
                abbr="other", city_id=None,
                defaults={"name": "Другое"})
            attrs['university'] = university
        # TODO: if where_did_you_learn.other selected, where_did_you_learn_other should be provided?
        return attrs

    def validate_stepic_id(self, value):
        return value.rsplit("/", maxsplit=1)[-1]

    def validate_github_login(self, value):
        return value.rsplit("/", maxsplit=1)[-1]
