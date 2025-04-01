import csv
import os
import io
import yadisk
from django.core.management import BaseCommand
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from courses.constants import SemesterTypes
from courses.models import Assignment, Semester
from learning.models import StudentAssignment
from users.models import StudentProfile, StudentTypes
from api.models import ExternalServiceToken

def get_max_assignment_grade(assignment: Assignment):
    assert isinstance(assignment, Assignment), f"Assignment object expected, {type(assignment)} object found"
    return assignment.studentassignment_set.all().aggregate(Max('score'))['score__max']


class Command(BaseCommand):
    help = "Weekly dump student enrollments csv and upload to yandex disk"

    def _create_parent_directories(self, client, path):
        """Ensure all parent directories exist on Yandex Disk."""
        parent_path = os.path.dirname(path)
        if not parent_path or client.exists(parent_path):
            return
        self._create_parent_directories(client, parent_path)
        client.mkdir(parent_path)

    def handle(self, *args, **options):
        with io.StringIO() as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow([_('Student ID'), _('Curriculum year'), _('Semester'), _('Course'), _('Branch'), _('Student type'), 
                                 _('Student Group'), _('Teacher'), _('Assignment'), _('Assignment status'), _('Assignment Grade'), 
                                 _('Maximum score'), _('Assignment count'), _('Maximum student score'), _('Grade'), _('Grade re-credited')])

            current_semester = Semester.get_current()
            current_curriculum_year = current_semester.year if current_semester.type == SemesterTypes.AUTUMN else current_semester.year - 1
            student_profiles = (StudentProfile.objects.filter(type__in=[StudentTypes.REGULAR, StudentTypes.PARTNER],
                                                             year_of_curriculum__in=[current_curriculum_year - 1, current_curriculum_year])
                                                        .select_related('user')
                                                        .prefetch_related('enrollment_set__course__assignment_set__studentassignment_set'))
            max_assignment_grades: dict[Assignment, int] = dict()
            for student_profile in student_profiles:
                user = student_profile.user
                for enrollment in student_profile.enrollment_set.all():
                    course = enrollment.course
                    assignments = course.assignment_set.all()
                    for assignment in assignments:
                        try:
                            student_assignment = StudentAssignment.objects.get(assignment=assignment, student=user)
                            if assignment not in max_assignment_grades:
                                max_assignment_grades[assignment] = get_max_assignment_grade(assignment)
                            max_assignment_grade = max_assignment_grades[assignment]
                            teacher = student_assignment.assignee.teacher if student_assignment.assignee is not None else ""
                            csv_writer.writerow([user.id, student_profile.year_of_curriculum, course.semester, course.meta_course, student_profile.branch.name, student_profile.get_type_display(), 
                                        enrollment.student_group, teacher, assignment.title, student_assignment.get_status_display(), student_assignment.score, 
                                        assignment.maximum_score, len(assignments), max_assignment_grade, enrollment.grade_honest, enrollment.is_grade_recredited])
                        except StudentAssignment.DoesNotExist:
                            # No student assignment for assignment {assignment} in course {course} and user {user}
                            pass

            csv_file.seek(0)
            client = yadisk.Client(token=ExternalServiceToken.objects.get(service_tag="syrop_yandex_disk").access_key,
                                    default_args={"overwrite" : True})
            with client:
                if not client.check_token():
                    raise AssertionError("Token seems to ne invalid. Is it expired?")
                
                # Используем ISO формат для имени файла
                today = timezone.now().date().isoformat()
                target_path = f"/ysda/weekly_student_assignments/student_assignments_{today}.csv"
                self._create_parent_directories(client, target_path)
                client.upload(io.BytesIO(csv_file.getvalue().encode()), target_path)
