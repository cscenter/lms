from rest_framework import serializers

from admission.models import Applicant


class ApplicantSerializer(serializers.ModelSerializer):
    # FIXME: validate course choices
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
            "experience", "online_education_experience"
            # CSC
            'campaign',
            "preferred_study_programs",
            "preferred_study_programs_dm_note",
            "preferred_study_programs_cs_note",
            "preferred_study_programs_se_note",
            "motivation", "probability",
            "additional_info",
            # Source
            "where_did_you_learn", "where_did_you_learn_other",
        )
