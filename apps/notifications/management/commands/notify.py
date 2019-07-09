# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from urllib.parse import urlparse

from django.apps import apps
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.encoding import smart_text
from django.utils.html import strip_tags, linebreaks

from learning.models import AssignmentNotification, \
    CourseNewsNotification
from users.constants import Roles
from notifications import NotificationTypes as notification_types

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

# Student and teacher groups which can access center site.
LEARNING_PARTICIPANTS_CENTER = {
    Roles.STUDENT,
    Roles.VOLUNTEER,
    Roles.GRADUATE,
    Roles.TEACHER,
}


def get_base_domain(notification):
    """
    XXX: we resolve notifications for students or teachers only.
    Don't care about interviewers or project reviewers.
    """
    receiver = notification.user
    if isinstance(notification, AssignmentNotification):
        course = notification.student_assignment.assignment.course
    elif isinstance(notification, CourseNewsNotification):
        course = notification.course_offering_news.course
    else:
        raise NotImplementedError()
    user_roles = receiver.roles
    if not user_roles.intersection(LEARNING_PARTICIPANTS_CENTER):
        if course.get_city() == "spb":
            return "compsciclub.ru"
        else:
            return "{}.compsciclub.ru".format(course.get_city())
    if isinstance(notification, AssignmentNotification):
        return f"{settings.LMS_SUBDOMAIN}.compscicenter.ru"
    return "compscicenter.ru"


def replace_hostname(url, new_hostname):
    """
    `core.urls.reverse` returns domain based on settings.SITE_ID value, but
    management command could be run from different envs
    (e.g. send notification for compsciclub.ru)
    """
    parsed = urlparse(url)
    replaced = parsed._replace(netloc=new_hostname,
                               # FIXME: Default value for scheme on server side?
                               scheme='https')
    return replaced.geturl()


def report(f, s):
    dt = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    f.write("{0} {1}".format(dt, s))


def send_notification(notification, template, context, f):
    """Sends email notification, then updates notification state in DB"""
    # XXX: Note that email is mandatory now
    if not notification.user.email:
        report(f, "User {0} doesn't have an email"
               .format(smart_text(notification.user)))
        notification.is_notified = True
        notification.save()
        return

    html_content = linebreaks(render_to_string(template['template_name'],
                                               context))
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives("[{}] {}".format(context['course_name'],
                                                  template['subject']),
                                 text_content,
                                 settings.DEFAULT_FROM_EMAIL,
                                 [notification.user.email])
    msg.attach_alternative(html_content, "text/html")
    report(f, "sending {0} ({1})".format(smart_text(notification),
                                         smart_text(template)))
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


def get_assignment_notification_context(notification: AssignmentNotification):
    base_domain = get_base_domain(notification)
    a_s = notification.student_assignment
    tz_override = None
    u = notification.user
    # Override timezone to enrolled students if course is online
    if a_s.assignment.course.is_correspondence and (
            u.is_student or u.is_volunteer):
        tz_override = settings.TIME_ZONES[notification.user.city_code]
    context = {
        'a_s_link_student': replace_hostname(a_s.get_student_url(), base_domain),
        'a_s_link_teacher': replace_hostname(a_s.get_teacher_url(), base_domain),
        # FIXME: rename
        'assignment_link': replace_hostname(a_s.assignment.get_teacher_url(), base_domain),
        'notification_created': notification.created_local(tz_override),
        'assignment_name': smart_text(a_s.assignment),
        'assignment_text': smart_text(a_s.assignment.text),
        'student_name': smart_text(a_s.student),
        'deadline_at': a_s.assignment.deadline_at_local(tz=tz_override),
        'course_name': smart_text(a_s.assignment.course.meta_course)
    }
    return context


def get_course_news_notification_context(notification: CourseNewsNotification):
    base_domain = get_base_domain(notification)
    course = notification.course_offering_news.course
    context = {
        'course_link': replace_hostname(course.get_absolute_url(), base_domain),
        'course_name': smart_text(course.meta_course),
        'course_news_name': notification.course_offering_news.title,
        'course_news_text': notification.course_offering_news.text,
    }
    return context


class Command(BaseCommand):
    help = 'Sends email notifications'
    can_import_settings = True

    def handle(self, *args, **options):
        # TODO: Looks ugly, rewrite it cls
        from django.conf import settings
        translation.activate(settings.LANGUAGE_CODE)

        notifications_assignments = (
            AssignmentNotification.objects
            .filter(is_unread=True, is_notified=False)
            .select_related("user")
            .prefetch_related(
                "user__groups",
                'student_assignment',
                'student_assignment__assignment',
                'student_assignment__assignment__course',
                'student_assignment__assignment__course__meta_course',
                'student_assignment__student'))
        for notification in notifications_assignments:
            context = get_assignment_notification_context(notification)
            template = get_assignment_notification_template(notification)
            send_notification(notification, template, context, self.stdout)

        notifications_course_news \
            = (CourseNewsNotification.objects
               .filter(is_unread=True, is_notified=False)
               .select_related("user")
               .prefetch_related(
                   'user__groups',
                   'course_offering_news',
                   'course_offering_news__course',
                   'course_offering_news__course__meta_course',
                   'course_offering_news__course__semester'))
        for notification in notifications_course_news:
            context = get_course_news_notification_context(notification)
            send_notification(notification, EMAIL_TEMPLATES['new_course_news'],
                              context, self.stdout)

        from notifications.models import Notification
        from notifications.registry import registry
        unread_notifications = (Notification.objects
                                .unread()
                                .filter(public=True, emailed=False)
                                .select_related("recipient"))
        # FIXME: I was wrong. It's hard to understand and debug. Refactor
        # id => code
        types_map = {v: k for k, v in
                     apps.get_app_config('notifications').type_map.items()}
        # TODO: skip EMPTY type notifications?
        # TODO: What if recipient have no email?
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
