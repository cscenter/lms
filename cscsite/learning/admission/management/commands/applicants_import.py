# -*- coding: utf-8 -*-
import logging

import tablib
from django.core.management import BaseCommand, CommandError
from django.utils import translation
from django.utils.functional import cached_property
from django.utils.timezone import now
from import_export import resources

from core.models import University
from learning.admission.models import Applicant, Campaign
from users.models import CSCUser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    Import applicants from yandex `feedback.csv`. Dry run by default.
    
    Add uuid4 with column name `uuid` before import file, if you want to update
    already existing records.
    """

    def add_arguments(self, parser):
        parser.add_argument('csv', metavar='CSV', help='path to csv file')
        parser.add_argument('--save',
                            action="store_true",
                            help='Run inside transaction, rollback in the end')

    def handle(self, *args, **options):
        csv_path = options["csv"]
        dry_run = not options["save"]
        data = tablib.Dataset().load(open(csv_path).read())
        if 'uuid' not in data.headers:
            raise CommandError("Add `uuid` column to prevent data duplication")
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


class ApplicantImportResource(resources.ModelResource):

    class Meta:
        model = Applicant
        import_id_fields = ['uuid']  # Get existing models by this field
        skip_unchanged = True

    @cached_property
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
            "Приложите текст вашей курсовой или дипломной работы, если хотите": "admin_note",
            "В разработке какого приложения, которым вы пользуетесь каждый день, вы хотели бы принять участие? Почему? Каких знаний вам для этого не хватает?": "preferred_study_programs_se_note",
            "Откуда вы узнали о CS центре?": "where_did_you_learn",
            "Откуда вы узнали о CS центре? (другое)": "where_did_you_learn_other",
            "Почему вы хотите учиться в CS центре?": "motivation",
            "Чем вы планируете заниматься после окончания обучения?": "your_future_plans",
            "Напишите любую дополнительную информацию о себе, которую хотите указать": "additional_info"
        }

    @cached_property
    def course_values(self):
        return {
            "1": CSCUser.COURSES.BACHELOR_SPECIALITY_1,
            "2": CSCUser.COURSES.BACHELOR_SPECIALITY_2,
            "3": CSCUser.COURSES.BACHELOR_SPECIALITY_3,
            "4": CSCUser.COURSES.BACHELOR_SPECIALITY_4,
            "5 (специалитет)": CSCUser.COURSES.SPECIALITY_5,
            "1 (магистратура)": CSCUser.COURSES.MASTER_1,
            "2 (магистратура)": CSCUser.COURSES.MASTER_2,
            "аспирант": CSCUser.COURSES.POSTGRADUATE,
            "выпускник университета": CSCUser.COURSES.GRADUATE,
        }

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        translation.activate('ru')
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
        to_replace = []
        for f in row:
            for code in other_cities:
                if f.startswith(code):
                    to_remove.append(f)
            if f.startswith(city_code):
                to_replace.append(f)
            # Also replace `None` values
            row[f] = row[f].strip()
            if f == 'where_did_you_learn' and not row[f]:
                row[f] = '<не указано>'
        # Remove columns related to other cities
        for f in to_remove:
            del row[f]
        # Replace prefixed name with name from model
        # We lose the order here, btw. `row` is an OrderedDict
        for f in to_replace:
            row[f[len(city_code) + 1:]] = row[f]
            del row[f]

        # Replace course name with enum value
        row['course'] = self.course_values[row['course']]

        # FK values for campaign and university already validated, but we can't
        # set them without additional query to DB. To do so, we should customize
        # FK widget `clean` method or directly set values in `import_obj` call.
        self.custom_fields = {}
        self.custom_fields["campaign_id"] = self.current_campaigns[city_code].pk
        del row['city']
        # Replace `university` name with university id
        # Throw an error if university names in csv not synced with DB values
        if row['university'] == 'Другое':
            university_id = self.universities_others[city_code]
        else:
            university_id = self.universities[row['university']]
        self.custom_fields["university_id"] = university_id
        del row['university']
        # Partially clean yandex_id, it should help in many cases
        if '@yandex.ru' in row['yandex_id'] or '@ya.ru' in row['yandex_id']:
            ya_login = row['yandex_id'].split('@yandex.ru', maxsplit=1)[0]
            row['yandex_id'] = ya_login.split('@ya.ru', maxsplit=1)[0]
        # Try to replace link to profile with login value
        pos = row['github_id'].find('github.com')
        if pos != -1:
            s = row['github_id'][pos + len('github.com') + 1:]
            row['github_id'] = s.split('/', maxsplit=1)[0]
        other_str = 'другое (укажите, что именно, в следующем поле)'
        if other_str in row['where_did_you_learn']:
            row['where_did_you_learn'] = row['where_did_you_learn'].replace(
                other_str, 'другое')

    def import_obj(self, obj, data, dry_run):
        super(ApplicantImportResource, self).import_obj(obj, data, dry_run)
        for attr_name, value in self.custom_fields.items():
            setattr(obj, attr_name, value)

    def before_save_instance(self, instance, using_transactions, dry_run):
        """Invoke clean method to normalize yandex_id"""
        instance.clean()


