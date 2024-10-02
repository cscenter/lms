from admission.constants import InterviewSections
from admission.management.commands._utils import CurrentCampaignMixin
from admission.models import Applicant, Comment, Interview
import csv
from core.models import Location
from datetime import datetime
from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from users.models import User


class Command(CurrentCampaignMixin, BaseCommand):
    help = """
    Create interview and interview comment for applicants with id from csv
    Example: ./manage.py create_interview_from_csv --date=2024-06-24 --section=PROGRAMMING --comment='МФТИ'
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--filename",
            type=str,
            default='ids.csv',
            help="csv file name",
        )
        parser.add_argument(
            "--delimiter",
            type=str,
            default=',',
            help="csv delimiter",
        )
        parser.add_argument(
            "--date",
            type=str,
            default="today",
            help="date of interview in YYYY-MM-DD format",
        )
        parser.add_argument(
            "--venue",
            type=str,
            default='Онлайн-собеседование в ШАД Москва 2024',
            help="venue of interview",
        )
        parser.add_argument(
            "--interviewer_id",
            type=int,
            default=15418,
            help="ID of interviewer",
        )
        parser.add_argument(
            "--score",
            type=int,
            default=5,
            help="interview score",
        )
        parser.add_argument(
            "--section",
            type=str,
            required=True,
            help="Section of interview",
        )
        parser.add_argument(
            "--comment",
            type=str,
            required=True,
            help="Comment text",
        )

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options, confirm=False)
        delimiter = options["delimiter"]
        filename = options["filename"]
        venue = Location.objects.get(name=options["venue"])
        date = timezone.now().date() if options["date"] == "today" \
            else datetime.strptime(options["date"], '%Y-%m-%d').date()
        interviewer = User.objects.get(pk=options["interviewer_id"])
        section = getattr(InterviewSections, options["section"])
        comment_text = options["comment"]
        score = options["score"]
        with open(filename) as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter)
            headers = next(reader)
            with transaction.atomic():
                for applicant_number, row in enumerate(reader):
                    id = row[0][-6:-1]
                    try:
                        applicant = Applicant.objects.get(id=id, campaign__in=campaigns)
                    except Applicant.DoesNotExist:
                        print(f'{id} does not exists')
                        raise
                    interview = Interview(
                        applicant=applicant,
                        status=Interview.COMPLETED,
                        section=section,
                        venue=venue,
                        date=date)
                    print(applicant)
                    interview.save()
                    interview.interviewers.add(interviewer)
                    comment = Comment(
                        interview=interview,
                        interviewer=interviewer,
                        text=comment_text,
                        score=score)
                    comment.save()
                if input(f'\nБудут созданы {applicant_number} завершенных собеседований по секции '
                         f'"{InterviewSections.get_choice(section).label}" на {date} c локацией "{venue}".\n'
                         f'Собеседущий {interviewer} поставит оценку {score} с комментарием "{comment_text}"\n'
                         f'Введите "y" для подтверждения: ') != "y":
                    raise CommandError("Error asking for approval. Canceled")


