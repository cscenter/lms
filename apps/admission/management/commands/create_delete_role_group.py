import csv

from django.db import transaction
from django.core.management import BaseCommand, CommandError

from admission.management.commands._utils import CurrentCampaignMixin
from core.models import Branch
from users.constants import Roles
from users.models import User
from django.conf import settings


class Command(CurrentCampaignMixin, BaseCommand):
    help = """
    Give or take back interviewer role from Users in csv
    Example of usage: 
        ./manage.py create_delete_role_group --filename=interviewers.csv --default_branch=msk --role=INTERVIEWER
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--filename",
            type=str,
            default='emails.csv',
            help="csv file name",
        )
        parser.add_argument(
            "--delimiter",
            type=str,
            default=',',
            help="csv delimiter",
        )
        parser.add_argument(
            "--default_branch",
            type=str,
            help="Default branch set if user doesn't have one",
        )
        parser.add_argument(
            "--take_back",
            action="store_true",
            default=False,
            dest="take_back",
            help="Take roles back"
        )
        parser.add_argument(
            "--role",
            type=str,
            required=True,
            help="Role to give or take back",
        )

    def handle(self, *args, **options):
        delimiter = options["delimiter"]
        filename = options["filename"]
        take_back = options["take_back"]
        default_branch = options["default_branch"]
        role = options["role"]
        available = Branch.objects.filter(
            active=True, site_id=settings.SITE_ID
        )
        cs = [c.code for c in available]
        if not default_branch or default_branch not in cs:
            msg = f"Provide the code of the branch with --default_branch. Options: {cs}"
            raise CommandError(msg)
        default_branch = Branch.objects.get(code=default_branch)
        with open(filename) as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter)
            with transaction.atomic():
                headers = next(reader)
                for row in reader:
                    user: User = User.objects.get(email__iexact=row[0])
                    branch = user.branch
                    if not branch:
                        self.stdout.write(self.style.WARNING(f"{user} doesn't have branch. Using default one"))
                        branch = default_branch
                    role = getattr(Roles, role)
                    if take_back:
                        user.remove_group(role, branch=branch)
                    else:
                        user.add_group(role, branch=branch)

