# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import logging
from datetime import datetime

from django.apps import apps
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.encoding import smart_text
from django.utils.html import strip_tags, linebreaks

from learning.models import AssignmentNotification, \
    CourseOfferingNewsNotification
from learning.settings import GROUPS_HAS_ACCESS_TO_CENTER, PARTICIPANT_GROUPS
from notifications import types as notification_types
from notifications.models import Type

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
    'new_courseoffering_news': {
        'title': "Добавлена новость к курсу",
        'template': "emails/new_courseoffering_news.html"
    },
    'deadline_changed': {
        'title': "Изменился срок сдачи домашнего задания",
        'template': "emails/deadline_changed.html"
    },
    'new_assignment': {
        'title': "Появилось новое домашнее задание",
        'template': "emails/new_assignment.html"
    },
    'enrollment_application': {
        'title': "Спасибо за заполнение заявки на поступление в CSC",
        'template': "emails/enrollment_application.html"
    }
}

# Student and teacher groups which can access center site.
LEARNING_PARTICIPANTS_CENTER = {
    PARTICIPANT_GROUPS.STUDENT_CENTER,
    PARTICIPANT_GROUPS.VOLUNTEER,
    PARTICIPANT_GROUPS.GRADUATE_CENTER,
    PARTICIPANT_GROUPS.TEACHER_CENTER,
}


def get_base_url(notification):
    """
    XXX: we resolve notifications for students or teachers only.
    Don't care about interviewers or project reviewers.
    """
    receiver = notification.user
    if isinstance(notification, AssignmentNotification):
        co = notification.student_assignment.assignment.course_offering
    elif isinstance(notification, CourseOfferingNewsNotification):
        co = notification.course_offering_news.course_offering
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
                'student_assignment__assignment__course_offering',
                'student_assignment__assignment__course_offering__course',
                'student_assignment__student')
        )

        for notification in notifications_assignments:
            base_url = get_base_url(notification)
            a_s = notification.student_assignment
            context = {'a_s_link_student':
                           base_url + reverse('a_s_detail_student',
                                              args=[a_s.pk]),
                       'a_s_link_teacher':
                           base_url + reverse('a_s_detail_teacher',
                                              args=[a_s.pk]),
                       'assignment_link':
                           base_url + reverse('assignment_detail_teacher',
                                              args=[a_s.assignment.pk]),
                       'notification_created': notification.created,
                       'assignment_name': smart_text(a_s.assignment),
                       'assignment_text': smart_text(a_s.assignment.text),
                       'student_name': smart_text(a_s.student),
                       'deadline_at': a_s.assignment.deadline_at,
                       'course_name': smart_text(a_s.assignment.course_offering.course)}
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

        notifications_courseoffering_news \
            = (CourseOfferingNewsNotification.objects
               .filter(is_unread=True, is_notified=False)
               .select_related("user")
               .prefetch_related(
                   'user__groups',
                   'course_offering_news',
                   'course_offering_news__course_offering',
                   'course_offering_news__course_offering__course',
                   'course_offering_news__course_offering__semester'))

        for notification in notifications_courseoffering_news:
            base_url = get_base_url(notification)
            course_offering = notification.course_offering_news.course_offering
            name = 'new_courseoffering_news'
            context = {'courseoffering_link':
                           base_url + course_offering.get_absolute_url(),
                       'courseoffering_name':
                       smart_text(course_offering.course),
                       'courseoffering_news_name':
                       notification.course_offering_news.title,
                       'courseoffering_news_text':
                       notification.course_offering_news.text,
                       'course_name':
                       smart_text(course_offering.course)}

            notify(notification, name, context, self.stdout)

        from notifications.models import Notification
        from notifications.registry import registry
        unread_notifications = (Notification.objects
                                .unread()
                                .filter(public=True, emailed=False)
                                .select_related("recipient"))

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
