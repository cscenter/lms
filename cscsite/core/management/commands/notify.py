# -*- coding: utf-8 -*-

import logging
from datetime import datetime

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
from learning.settings import AcademicRoles
from notifications import types as notification_types

logger = logging.getLogger(__name__)

EMAILS = {
    'new_comment_for_student': {
        'title': "Преподаватель оставил комментарий к решению задания",
        'template': "emails/new_comment_for_student.html"
    },
    'assignment_passed': {
        'title': "Студент сдал домашнее задание",
        'template': "emails/assignment_passed.html"
    },
    'new_comment_for_teacher': {
        'title': "Студент оставил комментарий к решению задания",
        'template': "emails/new_comment_for_teacher.html"
    },
    'new_course_news': {
        'title': "Добавлена новость к курсу",
        'template': "emails/new_course_news.html"
    },
    'deadline_changed': {
        'title': "Изменился срок сдачи домашнего задания",
        'template': "emails/deadline_changed.html"
    },
    'new_assignment': {
        'title': "Появилось новое домашнее задание",
        'template': "emails/new_assignment.html"
    },
}

# Student and teacher groups which can access center site.
LEARNING_PARTICIPANTS_CENTER = {
    AcademicRoles.STUDENT_CENTER,
    AcademicRoles.VOLUNTEER,
    AcademicRoles.GRADUATE_CENTER,
    AcademicRoles.TEACHER_CENTER,
}


def get_base_url(notification):
    """
    XXX: we resolve notifications for students or teachers only.
    Don't care about interviewers or project reviewers.
    """
    receiver = notification.user
    if isinstance(notification, AssignmentNotification):
        co = notification.student_assignment.assignment.course
    elif isinstance(notification, CourseNewsNotification):
        co = notification.course_offering_news.course
    else:
        raise NotImplementedError()
    user_groups = {g.pk for g in receiver.groups.all()}
    if not user_groups.intersection(LEARNING_PARTICIPANTS_CENTER):
        if co.get_city() == "spb":
            return "http://compsciclub.ru"
        else:
            return "http://{}.compsciclub.ru".format(co.get_city())
    return "https://compscicenter.ru"


def report(f, s):
    dt = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    f.write("{0} {1}".format(dt, s))


def notify(notification, name, context, f):
    if not notification.user.email:
        report(f, "user {0} doesn't have an email"
               .format(smart_text(notification.user)))
        notification.is_notified = True
        notification.save()
        return

    html_content = linebreaks(
        render_to_string(EMAILS[name]['template'], context))
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives("[{}] {}".format(context['course_name'],
                                                  EMAILS[name]['title']),
                                 text_content,
                                 settings.DEFAULT_FROM_EMAIL,
                                 [notification.user.email])
    msg.attach_alternative(html_content, "text/html")
    report(f, "sending {0} ({1})".format(smart_text(notification),
                                         smart_text(name)))
    msg.send()
    notification.is_notified = True
    notification.save()


class Command(BaseCommand):
    help = 'Sends notifications through email'
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
                'student_assignment__student')
        )

        for notification in notifications_assignments:
            base_url = get_base_url(notification)
            a_s = notification.student_assignment
            tz_override = None
            u = notification.user
            # Override timezone to enrolled students if course is online
            if a_s.assignment.course.is_correspondence and (
                    u.is_student_center or u.is_volunteer):
                tz_override = settings.TIME_ZONES[notification.user.city_code]
            context = {
                'a_s_link_student': base_url + a_s.get_student_url(),
                'a_s_link_teacher': base_url + a_s.get_teacher_url(),
                'assignment_link': base_url + a_s.assignment.get_teacher_url(),
                'notification_created': notification.created_local(tz_override),
                'assignment_name': smart_text(a_s.assignment),
                'assignment_text': smart_text(a_s.assignment.text),
                'student_name': smart_text(a_s.student),
                'deadline_at': a_s.assignment.deadline_at_local(tz=tz_override),
                'course_name': smart_text(a_s.assignment.course.meta_course)
            }
            if notification.is_about_creation:
                name = 'new_assignment'
            elif notification.is_about_deadline:
                name = 'deadline_changed'
            else:
                if notification.user == a_s.student:
                    name = 'new_comment_for_student'
                elif notification.is_about_passed:
                    name = 'assignment_passed'
                else:
                    name = 'new_comment_for_teacher'

            notify(notification, name, context, self.stdout)

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
            base_url = get_base_url(notification)
            course = notification.course_offering_news.course
            name = 'new_course_news'
            context = {
                'course_link': base_url + course.get_absolute_url(),
                'course_name': smart_text(course.meta_course),
                'course_news_name': notification.course_offering_news.title,
                'course_news_text': notification.course_offering_news.text,
            }

            notify(notification, name, context, self.stdout)

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
