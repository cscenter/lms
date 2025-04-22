import logging
from django.contrib import messages
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views import View

from core.models import Branch
from core.urls import reverse
from post_office.models import EmailTemplate
from staff.forms import SendLettersForm, ConfirmSendLettersForm
from staff.utils import send_emails
from study_programs.models import AcademicDiscipline
from users.mixins import CuratorOnlyMixin
from users.models import StudentProfile, StudentTypes
from learning.settings import StudentStatuses

logger = logging.getLogger(__name__)

class ConfirmView(CuratorOnlyMixin, View):
    """
    Class-based view for confirming and preparing email sending to students.
    
    This view handles:
    1. Processing the form submission with filter criteria
    2. Filtering students based on the criteria
    3. Displaying a confirmation page with the list of recipients
    4. Sending test emails when requested
    """
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for the form submission.
        """
        form = SendLettersForm(data=request.POST, request=request)
        
        logger.debug("Form data: %s", request.POST)
        logger.debug("Form is valid:  %s", form.is_valid())
        if form.errors:
            logger.debug("Form errors: %s", form.errors)
        
        if form.is_valid():
            return self.process_valid_form(form, request)
        else:
            return self.process_invalid_form(form, request)
    
    def process_valid_form(self, form, request):
        """
        Process a valid form submission.
        """
        branch = form.cleaned_data.get('branch', [])
        student_type = form.cleaned_data.get('type', [])
        year_of_admission = form.cleaned_data.get('year_of_admission', [])
        year_of_curriculum = form.cleaned_data.get('year_of_curriculum', [])
        status = form.cleaned_data.get('status', [])
        academic_disciplines = form.cleaned_data.get('academic_disciplines', [])
        email_template_id = form.cleaned_data.get('email_template', "")
        test_email = form.cleaned_data.get('test_email', "")
        scheduled_time = form.cleaned_data.get('scheduled_time')
        
        if 'submit_test' in request.POST:
            return self.handle_test_email(email_template_id, test_email, request)
        elif 'submit_send' in request.POST:
            return self.handle_send_emails(
                email_template_id, branch, year_of_admission, year_of_curriculum, 
                student_type, status, academic_disciplines, scheduled_time, request
            )
        
        return HttpResponseRedirect(reverse("staff:exports"))
    
    def process_invalid_form(self, form, request):
        """
        Process an invalid form submission.
        """
        for field, error_as_list in form.errors.items():
            label = form.fields[field].label if field in form.fields else field
            errors = "<br>".join(str(error) for error in error_as_list)
            messages.error(request, mark_safe(f"{label}:<br>{errors}"))
        
        return HttpResponseRedirect(reverse("staff:exports"))
    
    def handle_test_email(self, email_template_id, test_email, request):
        """
        Handle sending a test email.
        """
        try:
            email_template = EmailTemplate.objects.get(pk=email_template_id)
            
            send_emails([test_email], email_template.name, is_test=True)
            
            messages.success(request, _("Test sending to {0} of template '{1}'").format(test_email, email_template.name))
        except Exception as e:
            logger.exception("Error when sending test email: %s", str(e))
            messages.error(request, _("Error during test sending: {0}").format(str(e)))
        
        return HttpResponseRedirect(reverse("staff:exports"))
    
    def handle_send_emails(self, email_template_id, branch, year_of_admission, 
                          year_of_curriculum, student_type, status, 
                          academic_disciplines, scheduled_time, request):
        """
        Handle sending emails to selected students.
        """
        try:
            emails, filter_description = self.filter_students_for_emails(
                email_template_id, branch, year_of_admission, year_of_curriculum, 
                student_type, status, academic_disciplines, scheduled_time
            )
        except Exception as e:
            logger.exception("Error when collecting emails: %s", str(e))
            messages.error(request, _("Error collecting emails: {0}").format(str(e)))
            return HttpResponseRedirect(reverse("staff:exports"))
        
        template_obj = EmailTemplate.objects.get(pk=email_template_id)
        
        initial = {  
            'filter_description_display': '\n'.join(filter_description[:-1]),  
            'base_info_display': filter_description[-1],  
            'recipients_display': '\n'.join(emails),  
            'template_display': template_obj.name,  
            'email_template_id': email_template_id,
            'scheduled_time': scheduled_time.isoformat() if scheduled_time else ""
        }
        
        form = ConfirmSendLettersForm(initial=initial)
        
        return render(request, 'staff/confirm_send_letters.html', {'form': form})

    def filter_students_for_emails(self, email_template_id, branch, year_of_admission, year_of_curriculum, 
                    student_type, status, academic_disciplines, scheduled_time):
        """
        Filter student profiles based on criteria and return a list of email addresses.
        """
        query = Q(site_id=settings.SITE_ID)
        filter_description = []

        if branch:
            branch_ids = [int(b) for b in branch]
            query &= Q(branch_id__in=branch_ids)
            branch_names = Branch.objects.filter(pk__in=branch_ids).values_list('name', flat=True)
            filter_description.append(_("Branch") + f": {', '.join(branch_names)}")
        
        if student_type:
            query &= Q(type__in=student_type)
            student_type_names = [str(dict(StudentTypes.choices).get(t, t)) for t in student_type]
            filter_description.append(_("Student type") + f": {', '.join(student_type_names)}")
        
        if year_of_admission:
            query &= Q(year_of_admission__in=year_of_admission)
            filter_description.append(_("Admission year") + f": {', '.join(year_of_admission)}")
        
        if year_of_curriculum:
            query &= Q(year_of_curriculum__in=year_of_curriculum)
            filter_description.append(_("Curriculum year") + f": {', '.join(year_of_curriculum)}")
        
        if status:
            query &= Q(status__in=status)
            status_names = [str(StudentStatuses.values.get(s, s)) if s != "" else str(_("Studying")) for s in status]
            filter_description.append(_("Status") + f": {', '.join(status_names)}")
        
        if academic_disciplines:
            academic_discipline_ids = [int(ad) for ad in academic_disciplines]
            query &= Q(academic_disciplines__id__in=academic_discipline_ids)
            discipline_names = AcademicDiscipline.objects.filter(pk__in=academic_discipline_ids).values_list('name', flat=True)
            filter_description.append(_("Fields of study") + f": {', '.join(discipline_names)}")
        
        emails = list(StudentProfile.objects.filter(query).select_related('user').values_list('user__email', flat=True).distinct())
        
        if scheduled_time and scheduled_time > timezone.now():
            schedule_info = _(" (scheduled on {0})").format(scheduled_time.strftime('%d.%m.%Y %H:%M %Z'))
        else:
            schedule_info = _(" (at once)")
        filter_description.append(_("Sending {0} emails {1}").format(len(emails), schedule_info))
        
        return emails, filter_description
    
class SendView(CuratorOnlyMixin, View):
    """
    Class-based view for sending emails.
    """

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for the send letters.
        """
        if 'cancel_send' in request.POST:
            messages.info(request, _("Email sending canceled"))
            return HttpResponseRedirect(reverse("staff:exports"))
            
        if 'confirm_send' in request.POST:
            return self.handle_confirm_send(request)

        messages.warning(request, _("No action specified. Email sending canceled."))
        return HttpResponseRedirect(reverse("staff:exports"))

    
    def handle_confirm_send(self, request):
        """
        Handle the confirmation of sending emails.
        """
        form = ConfirmSendLettersForm(request.POST)
        
        if form.is_valid():
            email_template_id = form.cleaned_data.get('email_template_id')
            scheduled_time_str = form.cleaned_data.get('scheduled_time')
            emails = form.get_emails()
            
            try:
                email_template = EmailTemplate.objects.get(pk=email_template_id)
                send_emails(emails, email_template.name, scheduled_time_str)
                
                messages.success(
                    request, 
                    _("Successfully scheduled sending {0} emails of template '{1}'").format(len(emails) if emails else 0, email_template.name)
                )
            except Exception as e:
                logger.exception("Error sending emails: %s", str(e))
                messages.error(request, _("Error sending emails: {0}").format(str(e)))
        else:
            messages.error(request, _("Invalid form data. Email sending canceled."))
        
        return HttpResponseRedirect(reverse("staff:exports"))
