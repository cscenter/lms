from django.conf import settings
from django.utils.timezone import now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from admission.models import Applicant, University, Campaign
from learning.settings import AcademicDegreeLevels
from .fields import AliasedChoiceField


class ApplicantYandexFormSerializer(serializers.ModelSerializer):
    # TODO: в универах http://my.csc.test/narnia/admission/university/ надо убирать привязку к отделению. Нужна связь m2m для отделений

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
    # TODO: значение university => FK value (быстрый варик через aliases)
    university = AliasedChoiceField(
        choices=[
            ('БГУ', 25),
            ('БГУИР', 26),
            ('КПИ', 10),  # TODO: добавить
            ('МГТУ им. Баумана', 10),  # TODO: добавить
            ('МГУ', 18),
            ('МФТИ', 17),
            ('НГУ', 11),
            ('НИУ ВШЭ', 19),
            ('НИУ ИТМО', 9),  # FIXME: 9 - ИТМО, другое
            ('СПбГУ', 23),  # FIXME: привязка к заочке
            ('УрФУ', 21),
            ('Другое', 10),
        ]
    )
    scientific_work = serializers.CharField(
        allow_blank=True,
        label='Если у вас уже была/есть научная работа, расскажите о чем она')
    programming_experience = serializers.CharField(
        allow_blank=True,
        label='Расскажите о своем опыте программирования')
    shad_plus_rash = AliasedChoiceField(
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
        choices=[
            ('Да', True, 'Да'),
            ('Нет', False, 'Нет'),
        ],
        label='Планируете ли вы воспользоваться новым треком поступления?'
    )
    new_track_scientific_articles = serializers.CharField(
        allow_blank=True,
        label='Есть ли у вас научные статьи? Если да, то дайте их координаты.')
    new_track_projects = serializers.CharField(
        allow_blank=True,
        label='Есть ли у вас открытые проекты вашего авторства, или в которых вы участвовали '
              'в составе команды, на github или на каком-либо из подобных сервисов? '
              'Если да, дайте ссылки на них.')
    new_track_tech_articles = serializers.CharField(
        allow_blank=True,
        label='Есть ли у вас посты или статьи о технологиях? Если да, дайте ссылки на них.')
    new_track_project_details = serializers.CharField(
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
            new_track_fields = ["new_track_scientific_articles", "new_track_projects", "new_track_tech_articles",
                                "new_track_project_details"]
            for field_name in new_track_fields:
                additional_info.append(f"{self.fields[field_name].label}\n{data[field_name]}")
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

        # FIXME: not really sure I need this one
        if attrs.get('university_other'):
            university, created = University.objects.get_or_create(
                abbr="other", branch_id=None,
                defaults={"name": "Другое"})
            attrs['university'] = university
        return attrs
