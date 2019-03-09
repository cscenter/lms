from django.conf import settings
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from admission.constants import WHERE_DID_YOU_LEARN
from admission.models import Applicant, Campaign
from admission.tasks import register_in_yandex_contest


class ApplicantSerializer(serializers.ModelSerializer):
    where_did_you_learn = serializers.MultipleChoiceField(
        WHERE_DID_YOU_LEARN,
        allow_empty=False)
    preferred_study_programs = serializers.MultipleChoiceField(
        Applicant.STUDY_PROGRAMS, required=False)
    campaign = serializers.PrimaryKeyRelatedField(
        label='Отделение',
        queryset=Campaign.get_active())
    # Note: This field is marked as required on a form level only since
    # curators could insert applicant through admin interface
    # without full information about applicant.
    has_job = serializers.BooleanField(label='Вы сейчас работаете?')
    # FIXME: Replace with hidden field
    yandex_id = serializers.CharField(max_length=80)

    class Meta:
        model = Applicant
        fields = (
            # Personal info
            "surname", "first_name", "patronymic",
            "email", "phone",
            # Accounts
            "stepic_id", "github_id", "yandex_id",
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

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        if instance.pk:
            register_in_yandex_contest.delay(instance.pk,
                                             settings.LANGUAGE_CODE)
        return instance

    def validate(self, attrs):
        campaign = attrs['campaign']
        if (not campaign.city.is_online_branch and
                not attrs.get("preferred_study_programs")):
            raise serializers.ValidationError(
                detail='Вы не выбрали интересующие вас направления обучения')
        if not attrs.get('has_job'):
            to_delete = ('workplace', 'position')
            for attr in to_delete:
                if attr in attrs:
                    del attrs[attr]
        # TODO; where_did_you_learn_other, то where_did_you_learn должно содержать other и наоборот
        return attrs
