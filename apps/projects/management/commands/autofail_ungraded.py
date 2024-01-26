from django.core.management import BaseCommand, CommandError

from courses.constants import SemesterTypes
from courses.models import Semester
from learning.models import Enrollment
from learning.settings import GradeTypes

class Command(BaseCommand):
    help = """
    Set grade to fail for all ungraded students. Only in courses of current semester by default.
    Set --prev-sem flag to apply for courses from Autumn 2020 till previous semester.
    """

    def add_arguments(self, parser):
        parser.add_argument("site", type=str, help='Site to search for enrollments')
        parser.add_argument('--prev-sem', action='store_true', help='If flag is true, script works for previous '
                                                                    'semesters')

    def handle(self, *args, **options):
        site = options["site"]
        enrollments = Enrollment.objects.select_related("student_profile__branch__site", "course__semester")
        current_term = Semester.get_current()
        if options['prev_sem']:
            term = Semester.objects.get(year=2020, type=SemesterTypes.AUTUMN)
            enrollments = enrollments.filter(grade=GradeTypes.NOT_GRADED,
                                course__semester__lte=term,
                                course__semester__gt=current_term,
                                student_profile__branch__site__domain=site)
        else:
            enrollments = enrollments.filter(grade=GradeTypes.NOT_GRADED,
                                             course__semester=current_term,
                                             student_profile__branch__site__domain=site)
        graded = enrollments.update(grade=GradeTypes.UNSATISFACTORY)
        return str(graded)
