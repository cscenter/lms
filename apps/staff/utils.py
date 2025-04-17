from django.conf import settings
from core.models import Branch
from study_programs.models import AcademicDiscipline
from users.models import StudentProfile
from post_office.models import EmailTemplate


def get_curriculum_year_choices():
    """
    Retrieves all distinct curriculum years from student profiles.
    """
    years = StudentProfile.objects.filter(
        site_id=settings.SITE_ID, 
        year_of_curriculum__isnull=False
    ).values_list('year_of_curriculum', flat=True).order_by('-year_of_curriculum').distinct()
    return [(str(year), str(year)) for year in years]


def get_branche_choices():
    """
    Retrieves all branches for the current site.
    """
    branches = Branch.objects.filter(site_id=settings.SITE_ID)
    return [(str(b.pk), b.name) for b in branches]


def get_admission_year_choices():
    """
    Retrieves all distinct admission years from student profiles.
    """
    admission_years = StudentProfile.objects.filter(
        site_id=settings.SITE_ID, 
        year_of_admission__isnull=False
    ).values_list('year_of_admission', flat=True).order_by('-year_of_admission').distinct()
    return [(str(year), str(year)) for year in admission_years]


def get_academic_discipline_choices():
    """
    Retrieves all academic disciplines.
    """
    academic_disciplines = AcademicDiscipline.objects.all().order_by('name')
    return [(str(d.pk), d.name) for d in academic_disciplines]
        

def get_email_template_choices():
    """
    Retrieves all email templates.
    """
    email_templates = EmailTemplate.objects.all().order_by('-created')
    return [(str(t.pk), t.name) for t in email_templates]
