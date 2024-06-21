import csv

from django.db import transaction
from django.core.management import BaseCommand, CommandError

from core.models import Branch
from users.constants import Roles
from users.models import User, UserGroup
from django.conf import settings


class Command(BaseCommand):
    help = """
    Give or take back interviewer role from Users in csv
    Example of usage: 
        ./manage.py create_delete_role_group --filename=interviewers.csv --branch=msk --role=INTERVIEWER
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
            "--branch",
            type=str,
            help="Branch used for role",
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

    def get_group_or_none(self, user, **kwargs):
        try:
            return user.groups.get(**kwargs)
        except UserGroup.DoesNotExist:
            return None

    def handle(self, *args, **options):
        delimiter = options["delimiter"]
        filename = options["filename"]
        take_back = options["take_back"]
        branch = options["branch"]
        role = getattr(Roles, options["role"])
        available = Branch.objects.filter(
            active=True, site_id=settings.SITE_ID
        )
        cs = [c.code for c in available]
        if not branch or branch not in cs:
            msg = f"Provide the code of the branch with --branch. Options: {cs}"
            raise CommandError(msg)
        branch = Branch.objects.get(code=branch)
        with open(filename) as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter)
            with transaction.atomic():
                headers = next(reader)
                for row in reader:
                    user: User = User.objects.get(email__iexact=row[0])

                    if take_back:
                        if self.get_group_or_none(user, role=role, branch=branch, site_id=settings.SITE_ID) is None:
                            self.stdout.write(
                                self.style.WARNING(f'{user} does not has group with this role and branch'))
                            continue

                        user.remove_group(role, branch=branch)
                    else:
                        if self.get_group_or_none(user, role=role, branch__isnull=True, site_id=settings.SITE_ID):
                            self.stdout.write(
                                self.style.WARNING(f'{user} already has group with this role and with no branch'))
                            continue

                        if self.get_group_or_none(user, role=role, branch=branch, site_id=settings.SITE_ID):
                            self.stdout.write(
                                self.style.WARNING(f'{user} already has group with this role and branch'))
                            continue

                        user.add_group(role, branch=branch)

