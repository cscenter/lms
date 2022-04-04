from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from rest_framework.validators import UniqueTogetherValidator

from django.conf import settings
from django.utils.timezone import now

from admission.api.serializers import OpenRegistrationCampaignField
from admission.models import Applicant, Campaign
from admission.tasks import register_in_yandex_contest
from core.models import University as UniversityLegacy
from universities.models import University
from learning.settings import AcademicDegreeLevels

from .fields import AliasedChoiceField


class ApplicantYandexFormSerializer(serializers.ModelSerializer):
    is_studying = AliasedChoiceField(
        choices=[
            ('Да', True, 'Да'),
            ('Нет', False, 'Нет'),
        ]
    )
    branch = AliasedChoiceField(
        choices=[
            ('Москва', 'msk', 'Moscow'),
            ('Минск', 'minsk', 'Minsk'),
            ('Нижний Новгород', 'nnov', 'Nizhny Novgorod'),
            ('Екатеринбург', 'ekb', 'Yekaterinburg'),
            ('Заочное отделение', 'distance', 'Distance Learning'),
        ]
    )
    level_of_education = AliasedChoiceField(
        required=False,
        choices=[
            ('1', AcademicDegreeLevels.BACHELOR_SPECIALITY_1),
            ('2', AcademicDegreeLevels.BACHELOR_SPECIALITY_2),
            ('3', AcademicDegreeLevels.BACHELOR_SPECIALITY_3),
            ('4', AcademicDegreeLevels.BACHELOR_SPECIALITY_4),
            ('5', AcademicDegreeLevels.SPECIALITY_5),
            ('6', AcademicDegreeLevels.SPECIALITY_6),
            ('1 (магистратура)', AcademicDegreeLevels.MASTER_1),
            ('2 (магистратура)', AcademicDegreeLevels.MASTER_2),
            ('Учусь в аспирантуре', AcademicDegreeLevels.POSTGRADUATE),
            ('Другое', AcademicDegreeLevels.OTHER),
        ]
    )
    university = AliasedChoiceField(
        choices=[
            ('БГУ', 20),
            ('БГУИР', 21),
            ('КПИ', 23),
            ('МГТУ им. Баумана', 22),
            ('МГУ', 16),
            ('МФТИ', 15),
            ('НГУ', 12),
            ('ННГУ', 25),
            ('НИУ ВШЭ', 17),
            ('НИУ ИТМО', 24),
            ('СПбГУ', 19),
            ('УрФУ', 18),
            ('Другое', 1),
        ]
    )
    scientific_work = serializers.CharField(
        allow_blank=True,
        label='Если у вас уже была/есть научная работа, расскажите о чем она')
    programming_experience = serializers.CharField(
        allow_blank=True,
        label='Расскажите о своем опыте программирования')
    shad_plus_rash = AliasedChoiceField(
        required=False,
        choices=[
            ('Да', True, 'Да'),
            ('Нет', False, 'Нет'),
        ],
        label='Планируете ли вы поступать на совместную программу ШАД и РЭШ?'
    )
    ml_experience = serializers.CharField(
        label='Изучали ли вы раньше машинное обучение/анализ данных? Каким образом? '
              'Какие навыки удалось приобрести, какие проекты сделать?')
    new_track = AliasedChoiceField(
        required=False,
        write_only=True,
        choices=[
            ('Да', True, 'Да'),
            ('Нет', False, 'Нет'),
        ],
        label='Планируете ли вы воспользоваться новым треком поступления?'
    )
    new_track_scientific_articles = serializers.CharField(
        required=False,
        allow_blank=True,
        label='Есть ли у вас научные статьи? Если да, то дайте их координаты.')
    new_track_projects = serializers.CharField(
        required=False,
        allow_blank=True,
        label='Есть ли у вас открытые проекты вашего авторства, или в которых вы участвовали '
              'в составе команды, на github или на каком-либо из подобных сервисов? '
              'Если да, дайте ссылки на них.')
    new_track_tech_articles = serializers.CharField(
        required=False,
        allow_blank=True,
        label='Есть ли у вас посты или статьи о технологиях? Если да, дайте ссылки на них.')
    new_track_project_details = serializers.CharField(
        required=False,
        allow_blank=True,
        label='Расскажите более подробно о каком-нибудь из своих проектов. Что хотелось сделать? '
              'Какие нетривиальные технические решения вы использовали? '
              'В чём были трудности и как вы их преодолевали? '
              'Пожалуйста, сохраните свой ответ в файле .pdf, выложите его на Яндекс.Диск и поместите сюда ссылку. '
              'Если у вас уже есть статья на эту тему и вы давали на неё ссылку в предыдущем вопросе, '
              'то можете поставить здесь прочерк.')

    class Meta:
        model = Applicant
        fields = (
            "branch",
            # Personal info
            "last_name", "first_name", "patronymic", "yandex_login",
            "email", "phone", "living_place", "birth_date",

            # Education
            "university", "university_other", "is_studying", "faculty",
            "level_of_education", "year_of_graduation",

            "where_did_you_learn_other", "motivation",
            "scientific_work", "programming_experience", "shad_plus_rash", "ml_experience",
            "new_track", "new_track_scientific_articles", "new_track_projects", "new_track_tech_articles",
            "new_track_project_details",
        )

    def create(self, validated_data):
        data = {**validated_data}
        data['university_legacy'] = UniversityLegacy.objects.get(pk=data['university'])
        del data['university']
        # Contact fields about scientific and programming experiences into one
        experience = ""
        for field_name in ('scientific_work', 'programming_experience'):
            if data[field_name]:
                experience += f"{self.fields[field_name].label}\n{data[field_name]}"
        if experience:
            data["experience"] = experience
        # Store non-generic questions in .additional_info field
        additional_info = []
        if data.get('shad_plus_rash'):
            display_value = self.fields['shad_plus_rash'].to_representation(data.get('shad_plus_rash'))
            additional_info.append(f"{self.fields['shad_plus_rash'].label}\n{display_value}")
        if data.get('new_track'):
            display_value = self.fields['new_track'].to_representation(data.get('new_track'))
            additional_info.append(f"{self.fields['new_track'].label}\n{display_value}")
            # new_track_* fields are optional
            new_track_fields = ["new_track_scientific_articles", "new_track_projects", "new_track_tech_articles",
                                "new_track_project_details"]
            for field_name in new_track_fields:
                value = data.get(field_name, None)
                if value:
                    additional_info.append(f"{self.fields[field_name].label}\n{value}")
        data['additional_info'] = '\n\n'.join(additional_info)
        # Remove fields that are actually not present on Applicant model
        custom_fields = []
        all_fields = [f.name for f in Applicant._meta.get_fields(include_hidden=True)]
        for field_name in data:
            if field_name not in all_fields:
                custom_fields.append(field_name)
        for field_name in custom_fields:
            if field_name in data:
                del data[field_name]
        return super().create(data)

    def validate(self, attrs):
        current_year = now().year
        try:
            attrs['campaign'] = (Campaign.objects
                                 .get(year=current_year,
                                      current=True,
                                      branch__code=attrs['branch'],
                                      branch__site_id=settings.SITE_ID))
        except Campaign.DoesNotExist:
            raise ValidationError(f"Current campaign for branch code `{attrs['branch']}` "
                                  f"in {current_year} does not exist")
        if not UniversityLegacy.objects.filter(pk=attrs['university']).exists():
            raise ValidationError(f"University with pk=`{attrs['university']}` does not exist")
        return attrs


class UniversityCitySerializer(serializers.Serializer):
    is_exists = serializers.BooleanField()
    pk = serializers.IntegerField(required=False)
    city_name = serializers.CharField(required=False, max_length=255)


class ApplicationYDSFormSerializer(serializers.ModelSerializer):
    campaign = OpenRegistrationCampaignField(
        label='Отделение',
        error_messages={
            'does_not_exist': 'Приемная кампания окончена либо не существует',
            'incorrect_type': 'Некорректное значение идентификатора кампании'
        })
    shad_plus_rash = AliasedChoiceField(
        required=False,
        write_only=True,
        choices=[
            (True, True, 'Да'),
            (False, False, 'Нет'),
        ],
        label='Планируете ли вы поступать на совместную программу ШАД и РЭШ?'
    )
    rash_agreement = serializers.BooleanField(
        required=False,
        write_only=True
    )
    new_track = AliasedChoiceField(
        required=False,
        write_only=True,
        choices=[
            (True, True, 'Да'),
            (False, False, 'Нет'),
        ],
        label='Планируете ли вы воспользоваться новым треком поступления?'
    )
    new_track_scientific_articles = serializers.CharField(
        required=False,
        allow_blank=True,
        label='Есть ли у вас научные статьи? Если да, то дайте их координаты.')
    new_track_projects = serializers.CharField(
        required=False,
        allow_blank=True,
        label='Есть ли у вас открытые проекты вашего авторства, или в которых вы участвовали '
              'в составе команды, на github или на каком-либо из подобных сервисов? '
              'Если да, дайте ссылки на них.')
    new_track_tech_articles = serializers.CharField(
        required=False,
        allow_blank=True,
        label='Есть ли у вас посты или статьи о технологиях? Если да, дайте ссылки на них.')
    new_track_project_details = serializers.CharField(
        required=False,
        allow_blank=True,
        label='Расскажите более подробно о каком-нибудь из своих проектов. Что хотелось сделать? '
              'Какие нетривиальные технические решения вы использовали? '
              'В чём были трудности и как вы их преодолевали? '
              'Пожалуйста, сохраните свой ответ в файле .pdf, выложите его на Яндекс.Диск и поместите сюда ссылку. '
              'Если у вас уже есть статья на эту тему и вы давали на неё ссылку в предыдущем вопросе, '
              'то можете поставить здесь прочерк.')
    ml_experience = serializers.CharField(
        write_only=True,
        label='Изучали ли вы раньше машинное обучение/анализ данных? Каким образом? '
              'Какие навыки удалось приобрести, какие проекты сделать?')
    ticket_access = serializers.BooleanField(
        write_only=True,
        label='Мне был предоставлен билет на прошлом отборе в ШАД'
    )
    magistracy_and_shad = serializers.BooleanField(
        write_only=True,
        label='Планируете ли вы поступать в этом году на одну из совместных с ШАД магистерских программ?'
    )
    email_subscription = serializers.BooleanField(
        write_only=True,
        label='Я согласен (-на) на получение новостной и рекламной рассылки от АНО ДПО "ШАД" и ООО "ЯНДЕКС'
    )
    shad_agreement = serializers.BooleanField(
        required=True,
        write_only=True
    )
    university = serializers.PrimaryKeyRelatedField(queryset=University.objects.all())
    university_city = UniversityCitySerializer(write_only=True)
    # FIXME: Replace with hidden field since real value stores in session
    yandex_login = serializers.CharField(max_length=80)

    class Meta:
        model = Applicant
        fields = (
            # Personal info
            "last_name", "first_name", "patronymic",
            "email", "phone", "birth_date", "living_place",

            # Accounts
            "yandex_login",

            # Education
            "university_city", "university", "university_other",
            "faculty", "is_studying", "level_of_education", "year_of_graduation",

            # YDS
            "campaign",
            "motivation",
            "ml_experience",
            "ticket_access",
            "magistracy_and_shad",
            "email_subscription",
            "shad_agreement",

            # Rash
            "shad_plus_rash",
            "rash_agreement",

            # New track
            "new_track",
            "new_track_scientific_articles",
            "new_track_projects",
            "new_track_tech_articles",
            "new_track_project_details",

            # Source
            "where_did_you_learn_other",
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
                        "напишите на shad@yandex-team.ru с этой почты.")
        ]

    def __init__(self, instance=None, data=empty, **kwargs):
        super().__init__(instance, data, **kwargs)
        self.fields["patronymic"].required = True
        self.fields["living_place"].required = True
        if data is not empty and data:
            if "university_other" in data:
                # Make university optional cause its value should be empty in
                # case when `university_other` value provided. Set value
                # later in `.validate` method.
                self.fields["university"].required = False
            if data.get("is_studying"):
                self.fields["level_of_education"].required = True
            if data.get("shad_plus_rash"):
                self.fields['rash_agreement'].required = True
            msk_campaign = (Campaign.with_open_registration()
                            .filter(branch__site_id=settings.SITE_ID,
                                    branch__code='msk')
                            .first())
            if msk_campaign is not None:
                if data.get('campaign') == str(msk_campaign.pk):
                    self.fields["new_track"].required = True
                    self.fields["shad_plus_rash"].required = True

    def create(self, validated_data):
        data = {**validated_data}
        data['data'] = {
            'university_city': data.get('university_city'),
            'shad_agreement': data.get('shad_agreement'),
            'new_track': data.get('new_track'),
            'new_track_scientific_articles': data.get('new_track_scientific_articles'),
            'new_track_projects': data.get('new_track_projects'),
            'new_track_tech_articles': data.get('new_track_tech_articles'),
            'new_track_project_details': data.get('new_track_project_details'),

            'shad_plus_rash': data.get('shad_plus_rash'),
            'rash_agreement': data.get('rash_agreement'),

            'ticket_access': data.get('ticket_access'),
            'magistracy_and_shad': data.get('magistracy_and_shad'),
            'email_subscription': data.get('email_subscription'),
            'data_format_version': '0.1'
        }
        data['experience'] = data['ml_experience']
        # Remove fields that are actually not present on Applicant model
        custom_fields = []
        all_fields = [f.name for f in Applicant._meta.get_fields(include_hidden=True)]
        for field_name in data:
            if field_name not in all_fields:
                custom_fields.append(field_name)
        for field_name in custom_fields:
            if field_name in data:
                del data[field_name]
        return super().create(data)

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        if instance.pk:
            # TODO: better to add transaction.on_commit
            register_in_yandex_contest.delay(instance.pk,
                                             settings.LANGUAGE_CODE)
        return instance

    def validate(self, attrs):
        if not attrs.get('is_studying') and 'level_of_education' in attrs:
            del attrs['level_of_education']
        if attrs.get('shad_plus_rash') and not attrs.get('rash_agreement'):
            raise ValidationError("Необходимо согласиться с политикой РЭШ в отношении персональных данных.")
        return attrs
