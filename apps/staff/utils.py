from django.conf import settings
from core.models import Branch
from study_programs.models import AcademicDiscipline
from users.models import StudentProfile
from post_office.models import EmailTemplate, Email
from post_office import mail
from post_office.utils import get_email_template


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

def send_emails(emails, template, data=None, is_test=False):
        """
        Send emails using the post_office library.
        """
        template = get_email_template(template)
        email_from = settings.DEFAULT_FROM_EMAIL

        scheduled_time = data if data else None

        if is_test:
            emails_to_send = emails
        else:
            sent_emails = Email.objects.filter(to__in=emails, template=template).values_list("to", flat=True)  
            emails_to_send = [email for email in emails if email not in sent_emails]
        
        # SendRawEmail destinations must have length less than or equal to 500
        sent_count = 0
        for i in range(0, len(emails_to_send), 500):
            batch = emails_to_send[i:i+500]
            mail.send(  
                batch,  
                sender=email_from,  
                template=template,  
                context={},  
                render_on_delivery=True,  
                backend='ses',  
                scheduled_time=scheduled_time  
            )
            sent_count += len(batch)
            
        return sent_count
