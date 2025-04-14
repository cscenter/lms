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

from core.http import HttpRequest
from core.models import Branch
from core.urls import reverse
from post_office.models import EmailTemplate, Email
from post_office import mail
from post_office.utils import get_email_template
from staff.forms import SendLettersForm
from study_programs.models import AcademicDiscipline
from users.mixins import CuratorOnlyMixin
from users.models import StudentProfile, StudentTypes
from learning.settings import StudentStatuses

logger = logging.getLogger(__name__)


class SendLettersView(CuratorOnlyMixin, View):
    """
    Class-based view for sending letters to students.
    
    This view handles:
    1. Displaying the form for selecting students to send emails to
    2. Processing the form submission
    3. Showing a confirmation page before sending emails
    4. Sending test emails
    5. Sending actual emails to selected students
    """
    
    @classmethod
    def _send_emails(cls, emails, template, data=None):
        """
        Send emails using the post_office library.
        """
        template = get_email_template(template)
        email_from = "Школа анализа данных <noreply@yandexdataschool.ru>"

        scheduled_time = data if data else None

        sent_count = 0
        for recipient in emails:
            if not Email.objects.filter(to=recipient, template=template).exists():
                mail.send(
                    recipient,
                    sender=email_from,
                    template=template,
                    context={},
                    render_on_delivery=True,
                    backend='ses',
                    scheduled_time=scheduled_time,
                )
                sent_count += 1
        return sent_count
    
    @classmethod
    def send_letters(cls, email_template_id, branch, year_of_admission, year_of_curriculum, 
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
            status_names = [str(StudentStatuses.values.get(s, s)) for s in status]
            filter_description.append(_("Status") + f": {', '.join(status_names)}")
        
        if academic_disciplines:
            academic_discipline_ids = [int(ad) for ad in academic_disciplines]
            query &= Q(academic_disciplines__id__in=academic_discipline_ids)
            discipline_names = AcademicDiscipline.objects.filter(pk__in=academic_discipline_ids).values_list('name', flat=True)
            filter_description.append(_("Fields of study") + f": {', '.join(discipline_names)}")
        
        emails = list(StudentProfile.objects.filter(query).select_related('user').values_list('user__email', flat=True).distinct())
        
        if scheduled_time and  scheduled_time > timezone.now():
            schedule_info = f" (запланировано на {scheduled_time.strftime('%d.%m.%Y %H:%M %Z')})"
        else:
            schedule_info = " (сразу)"
        filter_description.append(f"Отправляем {len(emails)} emails{schedule_info}")
        
        return emails, filter_description
    
    def dispatch(self, request, *args, **kwargs):
        """
        Override dispatch to handle different actions based on POST parameters.
        """
        logger.debug("Session data at start: %s", dict(request.session))
        
        if 'confirm_send' in request.POST:
            return self.handle_confirm_send(request)
        
        if 'cancel_send' in request.POST:
            return self.handle_cancel_send(request)
        
        if 'confirm_have_been' in request.session:
            self.clear_session_data(request)
        
        if 'emails' in request.session and 'filter_description' in request.session:
            return self.show_confirmation_page(request)
        
        if request.method == 'POST':
            return self.post(request, *args, **kwargs)
        
        return HttpResponseRedirect(reverse("staff:exports"))
    
    def handle_confirm_send(self, request):
        """
        Handle the confirmation of sending emails.
        """
        email_template_id = request.session.get('email_template_id')
        emails = request.session.get('emails', [])
        scheduled_time = request.session.get('scheduled_time')
        
        try:
            email_template = EmailTemplate.objects.get(pk=email_template_id)
            self._send_emails(emails, email_template.name, scheduled_time)
            
            self.clear_session_data(request)
            
            logger.debug("Session data after confirm: %s", dict(request.session))
            
            messages.success(
                request, 
                f"Успешно запланирована откравка {len(emails)} писем шаблона '{email_template.name}'"
            )
        except Exception as e:
            logger.exception("Error sending emails: %s", str(e))
            messages.error(request, f"Ошибка при отправке писем: {str(e)}")
        
        return HttpResponseRedirect(reverse("staff:exports"))
    
    def handle_cancel_send(self, request):
        """
        Handle the cancellation of sending emails.
        """
        self.clear_session_data(request)
        
        logger.debug("Session data after cancel: %s", dict(request.session))
        
        messages.info(request, "Отправка писем отменена")
        
        return HttpResponseRedirect(reverse("staff:exports"))
    
    def show_confirmation_page(self, request):
        """
        Show the confirmation page before sending emails.
        """
        request.session["confirm_have_been"] = True
        emails = request.session.get('emails', [])
        filter_description = request.session.get('filter_description', [])
        template_id = request.session.get('email_template_id', [])
        if template_id:
            template = EmailTemplate.objects.get(pk=template_id).name
        
        logger.debug("Session data in confirmation block: %s", dict(request.session))
        
        context = {
            'emails': emails,
            'email_count': len(emails),
            'filter_description': filter_description,
            'template': template,
        }
        
        return render(request, 'staff/confirm_send_letters.html', context)
    
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for the form submission.
        """
        form = SendLettersForm(data=request.POST, request=request)
        
        logger.debug("Form data: %s", request.POST)
        logger.debug("Form is valid: %s", form.is_valid())
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
    
    def handle_test_email(self, email_template_id, test_email, request):
        """
        Handle sending a test email.
        """
        try:
            email_template = EmailTemplate.objects.get(pk=email_template_id)
            
            self._send_emails([test_email], email_template.name)
            
            messages.success(request, f"Тестовая отправка {test_email} шаблона '{email_template.name}'")
        except Exception as e:
            logger.exception("Error when sending test email: %s", str(e))
            messages.error(request, f"Ошибка при тестовой отправке: {str(e)}")
        
        return HttpResponseRedirect(reverse("staff:exports"))
    
    def handle_send_emails(self, email_template_id, branch, year_of_admission, 
                          year_of_curriculum, student_type, status, 
                          academic_disciplines, scheduled_time, request):
        """
        Handle sending emails to selected students.
        """
        try:
            if scheduled_time:
                request.session['scheduled_time'] = scheduled_time.isoformat()
            else:
                request.session['scheduled_time'] = None


            emails, filter_description = self.send_letters(
                email_template_id, branch, year_of_admission, year_of_curriculum, 
                student_type, status, academic_disciplines, scheduled_time
            )
            
            request.session['email_template_id'] = email_template_id
            request.session['emails'] = emails
            request.session['filter_description'] = filter_description
            
            return HttpResponseRedirect(reverse("staff:send_letters"))
        except Exception as e:
            logger.exception("Error when collecting emails: %s", str(e))
            messages.error(request, f"Ошибка при сборе почт: {str(e)}")
        
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
    
    def clear_session_data(self, request):
        """
        Clear the session data related to sending emails.
        """
        request.session.pop('email_template_id', None)
        request.session.pop('emails', None)
        request.session.pop('scheduled_time', None)
        request.session.pop('filter_description', None)
        request.session.pop('confirm_have_been', None)
        
        request.session.modified = True
        request.session.save()


def send_letters_view(request: HttpRequest):
    """
    Function-based view for sending letters to students.
    This is a wrapper around the class-based view for backward compatibility.
    """
    view = SendLettersView.as_view()
    return view(request)
