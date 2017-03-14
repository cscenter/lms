# -*- coding: utf-8 -*-
import json
import logging
import uuid

import tablib
from django.core.management import BaseCommand, CommandError
from django.utils.timezone import now
from import_export import resources

from core.models import University
from learning.admission.models import Applicant, Campaign

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Import applicants from yandex `feedback.csv`"""

    def add_arguments(self, parser):
        parser.add_argument('csv', metavar='CSV', help='path to csv file')
        parser.add_argument('--dry-run',
                            action="store_true",
                            help='Run inside transaction, rollback in the end')

    def handle(self, *args, **options):
        csv_path = options["csv"]
        dry_run = options["dry_run"]

        data = tablib.Dataset().load(open(csv_path).read())
        applicant_resource = ApplicantImportResource()

        result = applicant_resource.import_data(data, dry_run=dry_run,
                                                raise_errors=False,
                                                collect_failed_rows=False)
        self.handle_errors(result)
        logger.debug("Import successfully finished.")

    @staticmethod
    def handle_errors(result):
        if result.has_errors():
            for error in result.base_errors:
                logger.debug(error)
            for line, errors in result.row_errors():
                for error in errors:
                    logger.debug("Line {} - {}".format(line + 1, error.error))



# TODO: Process `university` field
# TODO: Autocorrect yandex id (remove @ya.ru @yandex.ru and so on.)
# TODO: convert course text value to CSCUser.COURSES numeric value?
# FIXME: Кампания по набору теперь должна вычисляться динамически.
# FIXME: Duplicate info for `course` column from `additional_info` if set `other`"""
class ApplicantImportResource(resources.ModelResource):

    class Meta:
        model = Applicant
        import_id_fields = ['uuid']  # Get existing models by this field
        skip_unchanged = True

    @property
    def headers(self):
        return {
            "Фамилия": "second_name",
            "Имя": "first_name",
            "Отчество": "last_name",
            "Номер телефона": "phone",
            "Адрес электронной почты": "email",
            "Город": "city",
            "Университет (и иногда факультет), в котором вы учитесь или который закончили": "spb_university",
            "Университет, в котором вы учитесь или который закончили": "nsk_university",
            "Введите название университета": "university_other",
            "Факультет, специальность или кафедра, на которой вы учитесь или которую закончили": "faculty",
            "Курс, на котором вы учитесь": "course",
            "Вы сейчас работаете?": "has_job",
            "Место работы": "workplace",
            "Должность": "position",
            "Расскажите о своём опыте программирования и исследований": "experience",
            "Укажите свой логин на Яндексе": "yandex_id",
            "Укажите свой ID на Stepik.org, если есть": "stepic_id",
            "Оставьте ссылку на свой аккаунт на GitHub, если есть": "github_id",
            "Какие направления обучения из трёх вам интересны в CS центре?": "spb_preferred_study_programs",
            "Какие направления обучения из двух вам интересны в CS центре?": "nsk_preferred_study_programs",
            "Почему вам интересен анализ данных? Какие повседневные задачи решаются с помощью анализа данных?": "preferred_study_programs_dm_note",
            "Какие области Computer Science вам интересно было бы изучить?": "preferred_study_programs_cs_note",
            "Приложите текст вашей курсовой или дипломной работы, если хотите": "graduate_work",
            "В разработке какого приложения, которым вы пользуетесь каждый день, вы хотели бы принять участие? Почему? Каких знаний вам для этого не хватает?": "preferred_study_programs_se_note",
            "Откуда вы узнали о CS центре?": "where_did_you_learn",
            "Откуда вы узнали о CS центре? (другое)": "where_did_you_learn_other",
            "Почему вы хотите учиться в CS центре?": "motivation",
            "Чем вы планируете заниматься после окончания обучения?": "your_future_plans",
            "Напишите любую дополнительную информацию о себе, которую хотите указать": "additional_info"
        }

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        if "id" in dataset.headers:
            del dataset["id"]

        # Replace headers
        new_headers = []
        for h in dataset.headers:
            new_header = self.headers.get(h, h)
            new_headers.append(new_header)
        dataset.headers = new_headers

        # Attach current campaigns
        today = now()
        self.current_campaigns = {}
        for campaign in Campaign.objects.filter(year=today.year).all():
            self.current_campaigns[campaign.city_id] = campaign

        # Cache universities
        universities = University.objects.only("pk", "city_id", "name").values()
        # For each city we have special university record `Другое`.
        self.universities_others = {}
        for u in universities:
            if u['name'] == 'Другое':
                self.universities_others[u['city_id']] = u['id']

        self.universities = {u["name"]: u["id"] for u in universities}

    def before_import_row(self, row, **kwargs):
        """Remove unrelated data and clean"""

        if row['city'] == 'Санкт-Петербург':
            city_code = 'spb'
        elif row['city'] == 'Новосибирск':
            city_code = 'nsk'
        else:
            raise ValueError("Unknown city name")
        other_cities = [c for c in self.current_campaigns if c != city_code]
        to_remove = []
        for f in row:
            for code in other_cities:
                if f.startswith(code):
                    to_remove.append(f)
        for f in to_remove:
            del row[f]
        # Replace prefixed name with name from model
        # We lose order here, btw. `row` is an OrderedDict
        to_replace = [f for f in row if f.startswith(city_code)]
        for f in to_replace:
            row[f[len(city_code) + 1:]] = row[f]
            del row[f]
        # TODO: process other fields
        #FIXME: ок, я не могу здесь указать campaign_id и university_id, import_export их не признаёт.
        #FIXME: Нужно захукнуться в before_import_row?
        # Прочекать university_id. Как отлавливать ошибки, если нет нужных campaign_id?
        row["campaign_id"] = self.current_campaigns[city_code].pk
        del row['city']
        row["uuid"] = str(uuid.uuid4())
        # Replace `university` name with university id
        if row['university'] == 'Другое':
            row['university_id'] = self.universities_others[city_code]
        else:
            row['university_id'] = self.universities[row['university']]
        del row['university']
        print(row)

    def import_field(self, field, obj, data):
        if field.attribute and field.column_name in data:
            if field.column_name == "where_did_you_learn":
                data[field.column_name] = data[field.column_name].strip()
                if not data[field.column_name]:
                    data[field.column_name] = "<не указано>"
            if data[field.column_name] == "None":
                data[field.column_name] = ""
            field.save(obj, data)

    def before_save_instance(self, instance, using_transactions, dry_run):
        """Invoke clean method to normalize yandex_id"""
        instance.clean()


