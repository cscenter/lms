# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from functools import partial
from typing import Dict

from django.apps import apps
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.mail.backends import smtp
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.encoding import smart_str
from django.utils.html import strip_tags, linebreaks
from django.utils.module_loading import import_string
from django_ses import SESBackend

from core.models import SiteConfiguration, Branch
from core.urls import replace_hostname
from courses.models import Course
from learning.models import AssignmentNotification, \
    CourseNewsNotification
from notifications import NotificationTypes as notification_types
from users.models import User

logger = logging.getLogger(__name__)

EMAIL_TEMPLATES = {
    'new_comment_for_student': {
        'subject': "Преподаватель оставил комментарий к решению задания",
        'template_name': "emails/new_comment_for_student.html"
    },
    'assignment_passed': {
        'subject': "Студент сдал домашнее задание",
        'template_name': "emails/assignment_passed.html"
    },
    'new_comment_for_teacher': {
        'subject': "Студент оставил комментарий к решению задания",
        'template_name': "emails/new_comment_for_teacher.html"
    },
    'new_course_news': {
        'subject': "Добавлена новость к курсу",
        'template_name': "emails/new_course_news.html"
    },
    'deadline_changed': {
        'subject': "Изменился срок сдачи домашнего задания",
        'template_name': "emails/deadline_changed.html"
    },
    'new_assignment': {
        'subject': "Появилось новое домашнее задание",
        'template_name': "emails/new_assignment.html"
    },
}


# TODO: In some cases by email template we could predict participant role
#  and avoid additional db hits
def resolve_course_participant_branch(course: Course, participant: User):
    """
    Base on Branch model instance it's possible to say where all links
    in a message will lead to and what email address use to send the message
    (FROM header)

    Note:
        This method doesn't check actual course participant role
    """
    enrollment = participant.get_enrollment(course.pk)
    # Enrollment stores student profile they used to enroll in the course
    if enrollment:
        branch = enrollment.student_profile.branch
    else:
        # Fallback to the main branch of the course
        branch = course.main_branch
    return branch


def report(f, s):
    dt = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    f.write("{0} {1}".format(dt, s))


def send_notification(notification, template, context, stdout,
                      site_settings: SiteConfiguration):
    """Sends email notification, then updates notification state in DB"""
    # XXX: Note that email is mandatory now
    if not notification.user.email:
        report(stdout, f"User {notification.user} has no email")
        notification.is_notified = True
        notification.save()
        return

    connection = get_email_connection(site_settings)
    from_email = site_settings.default_from_email
    subject = "[{}] {}".format(context['course_name'], template['subject'])
    html_content = linebreaks(render_to_string(template['template_name'],
                                               context))
    text_content = strip_tags(html_content)
    msg = EmailMultiAlternatives(subject=subject,
                                 body=text_content,
                                 from_email=from_email,
                                 to=[notification.user.email],
                                 connection=connection)
    msg.attach_alternative(html_content, "text/html")
    report(stdout, f"sending {notification} ({template})")
    msg.send()
    notification.is_notified = True
    notification.save()


def get_assignment_notification_template(notification: AssignmentNotification):
    if notification.is_about_creation:
        template_code = 'new_assignment'
    elif notification.is_about_deadline:
        template_code = 'deadline_changed'
    elif notification.is_about_passed:
        template_code = 'assignment_passed'
    elif notification.user == notification.student_assignment.student:
        template_code = 'new_comment_for_student'
    else:
        template_code = 'new_comment_for_teacher'
    return EMAIL_TEMPLATES[template_code]


def get_domain_name(branch: Branch, site_settings: SiteConfiguration) -> str:
    domain_name = branch.site.domain
    if site_settings.lms_subdomain:
        subdomain = site_settings.lms_subdomain
    else:
        # This naive conversion works with regular students only
        subdomain = branch.code.lower()
        # spb.compsciclub.ru -> compsciclub.ru
        if subdomain == site_settings.default_branch_code:
            subdomain = ''
    if subdomain:
        domain_name = f"{subdomain}.{domain_name}"
    return domain_name


def _get_abs_url_builder(domain_name):
    # Assume settings.DEFAULT_URL_SCHEME has the same value for all sites
    return partial(replace_hostname, new_hostname=domain_name)


def get_assignment_notification_context(
        notification: AssignmentNotification,
        participant_branch: Branch,
        site_settings: SiteConfiguration) -> Dict:
    a_s = notification.student_assignment
    tz_override = notification.user.get_timezone()
    domain_name = get_domain_name(participant_branch, site_settings)
    abs_url_builder = _get_abs_url_builder(domain_name)
    context = {
        'a_s_link_student': abs_url_builder(a_s.get_student_url()),
        'a_s_link_teacher': abs_url_builder(a_s.get_teacher_url()),
        # FIXME: rename
        'assignment_link': abs_url_builder(a_s.assignment.get_teacher_url()),
        'notification_created': notification.created_local(tz_override),
        'assignment_name': smart_str(a_s.assignment),
        'assignment_text': smart_str(a_s.assignment.text),
        'student_name': smart_str(a_s.student),
        'deadline_at': a_s.assignment.deadline_at_local(tz=tz_override),
        'course_name': smart_str(a_s.assignment.course.meta_course)
    }
    return context


def get_course_news_notification_context(
        notification: CourseNewsNotification,
        participant_branch: Branch,
        site_settings: SiteConfiguration) -> Dict:
    domain_name = get_domain_name(participant_branch, site_settings)
    abs_url_builder = _get_abs_url_builder(domain_name)
    course = notification.course_offering_news.course
    context = {
        'course_link': abs_url_builder(course.get_absolute_url()),
        'course_name': smart_str(course.meta_course),
        'course_news_name': notification.course_offering_news.title,
        'course_news_text': notification.course_offering_news.text,
    }
    return context


def get_email_connection(site_settings):
    # FIXME: temporarily disable resolving connection at runtime until dkim will be enabled on @yandexdataschool.ru
    return get_connection(settings.EMAIL_BACKEND)
    email_backend = import_string(site_settings.email_backend)
    if issubclass(email_backend, smtp.EmailBackend):
        decrypted = site_settings.decrypt(site_settings.email_host_password)
        connection = smtp.EmailBackend(host=site_settings.email_host,
                                       port=site_settings.email_port,
                                       username=site_settings.email_host_user,
                                       password=decrypted,
                                       use_tls=site_settings.email_use_tls,
                                       use_ssl=site_settings.email_use_ssl)
    elif issubclass(email_backend, SESBackend):
        # AWS settings are not depends on site configuration
        connection = SESBackend()
    else:
        connection = get_connection(site_settings.email_backend,
                                    fail_silently=False)
    return connection


def send_assignment_notifications(site_configurations, stdout) -> None:
    prefetch = [
        'user__groups',
        'student_assignment',
        'student_assignment__assignment',
        'student_assignment__assignment__course',
        'student_assignment__assignment__course__meta_course',
        'student_assignment__student',
    ]
    notifications = (AssignmentNotification.objects
                     .filter(is_unread=True,
                             is_notified=False)
                     .select_related("user", "user__branch")
                     .prefetch_related(*prefetch))
    for notification in notifications:
        template = get_assignment_notification_template(notification)
        course = notification.student_assignment.assignment.course
        branch = resolve_course_participant_branch(course, notification.user)
        site_settings: SiteConfiguration = site_configurations[branch.site_id]
        context = get_assignment_notification_context(
            notification, branch, site_settings)
        send_notification(notification, template, context, stdout, site_settings)


def send_course_news_notifications(site_configurations, stdout) -> None:
    prefetch = [
        'user__groups',
        'course_offering_news',
        'course_offering_news__course',
        'course_offering_news__course__meta_course',
        'course_offering_news__course__semester',
    ]
    notifications = (CourseNewsNotification.objects
                     .filter(is_unread=True, is_notified=False)
                     .select_related("user")
                     .prefetch_related(*prefetch))
    for notification in notifications:
        template = EMAIL_TEMPLATES['new_course_news']
        course = notification.course_offering_news.course
        branch = resolve_course_participant_branch(course, notification.user)
        site_settings: SiteConfiguration = site_configurations[branch.site_id]
        context = get_course_news_notification_context(notification,
                                                       branch, site_settings)
        send_notification(notification, template, context, stdout, site_settings)


class Command(BaseCommand):
    help = 'Sends email notifications'
    can_import_settings = True

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)
        # Some configuration (like SMTP settings) should be resolved at runtime
        site_settings = (SiteConfiguration.objects
                         .filter(enabled=True)
                         .select_related('site'))
        site_settings = {s.site_id: s for s in site_settings}

        send_assignment_notifications(site_settings, self.stdout)

        send_course_news_notifications(site_settings, self.stdout)

        from notifications.models import Notification
        from notifications.registry import registry
        unread_notifications = (Notification.objects
                                .unread()
                                .filter(public=True, emailed=False)
                                .select_related("recipient"))
        # FIXME: Refactor
        # id => code
        types_map = {v: k for k, v in
                     apps.get_app_config('notifications').type_map.items()}
        # TODO: skip EMPTY type notifications?
        for notification in unread_notifications:
            try:
                code = types_map[notification.type_id]
            except KeyError:
                # On notification type deletion, we should cascading
                # delete all notifications, low chance of error this type.
                logger.error("Couldn't map code to type_id {}. "
                             "Mark as deleted.".format(notification.type_id))
                Notification.objects.filter(pk=notification.pk).update(
                    deleted=True)
                continue
            notification_type = getattr(notification_types, code)
            if notification_type in registry:
                registry[code].notify(notification)
            else:
                logger.warning("Handler for type '{}' not registered. "
                               "Mark as deleted.".format(code))
                Notification.objects.filter(pk=notification.pk).update(
                    deleted=True)

        translation.deactivate()
