# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.encoding import smart_text
from django.utils.html import strip_tags, linebreaks

from learning.models import AssignmentNotification, \
    CourseOfferingNewsNotification

# import cscsite.urls


EMAILS = {'new_comment_for_student':
          {'title': "Преподаватель оставил комментарий к решению задания",
           'template': "emails/new_comment_for_student.html"},
          'new_comment_for_teacher':
          {'title': "Студент оставил комментарий к решению задания",
           'template': "emails/new_comment_for_teacher.html"},
          'new_courseoffering_news':
          {'title': "Добавлена новость к курсу",
           'template': "emails/new_courseoffering_news.html"},
          'deadline_changed':
          {'title': "Изменился срок сдачи домашнего задания",
           'template': "emails/deadline_changed.html"},
          'new_assignment':
          {'title': "Появилось новое домашнее задание",
           'template': "emails/new_assignment.html"}}


def report(s):
    print("{0} {1}".format(datetime.now().strftime("%Y.%m.%d %H:%M:%S"), s))


def notify(notification, name, context):
    if not notification.user.email:
        report("user {0} doesn't have an email"
               .format(smart_text(notification.user)))
        notification.is_notified = True
        notification.save()
        return

    html_content = linebreaks(
        render_to_string(EMAILS[name]['template'], context))
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(EMAILS[name]['title'],
                                 text_content,
                                 settings.DEFAULT_FROM_EMAIL,
                                 [notification.user.email])
    msg.attach_alternative(html_content, "text/html")
    report("sending {0} ({1})".format(smart_text(notification),
                                      smart_text(name)))
    msg.send()
    notification.is_notified = True
    notification.save()


class Command(BaseCommand):
    help = 'Sends notifications through email'
    can_import_settings = True

    def handle(self, *args, **options):
        from django.conf import settings
        translation.activate(settings.LANGUAGE_CODE)

        notifications_assignments \
            = (AssignmentNotification.objects
               .filter(is_unread=True, is_notified=False)
               .prefetch_related(
                   'user',
                   'assignment_student',
                   'assignment_student__assignment',
                   'assignment_student__assignment__course_offering',
                   'assignment_student__assignment__course_offering__course',
                   'assignment_student__student'))

        for notification in notifications_assignments:
            a_s = notification.assignment_student
            # FIXME: reverse doesn't work in management,
            # investigate, hardcode for now
            context = {'a_s_link_student':
                       ("http://compscicenter.ru/learning/assignments/{0}/"
                        .format(a_s.pk)),
                       'a_s_link_teacher':
                       ("http://compscicenter.ru/"
                        "teaching/assignments/submissions/{0}/"
                        .format(a_s.pk)),
                       'assignment_link':
                       ("http://compscicenter.ru/teaching/assignments/{0}/"
                        .format(a_s.assignment.pk)),
                       'assignment_name':
                       smart_text(a_s.assignment),
                       'assignment_text':
                       smart_text(a_s.assignment.text),
                       'student_name':
                       smart_text(a_s.student),
                       'deadline_at':
                       a_s.assignment.deadline_at}
            if notification.is_about_creation:
                name = 'new_assignment'
            elif notification.is_about_deadline:
                name = 'deadline_changed'
            else:
                if notification.user == a_s.student:
                    name = 'new_comment_for_student'
                else:
                    name = 'new_comment_for_teacher'

            notify(notification, name, context)

        notifications_courseoffering_news \
            = (CourseOfferingNewsNotification.objects
               .filter(is_unread=True, is_notified=False)
               .prefetch_related(
                   'user',
                   'course_offering_news',
                   'course_offering_news__course_offering',
                   'course_offering_news__course_offering__course',
                   'course_offering_news__course_offering__semester'))

        for notification in notifications_courseoffering_news:
            course_offering = notification.course_offering_news.course_offering

            name = 'new_courseoffering_news'
            context = {'courseoffering_link':
                       # FIXME: see above for a note about 'reverse'
                       ("http://compscicenter.ru/courses/{0}/{1}/"
                        .format(course_offering.course.slug,
                                course_offering.semester.slug)),
                       'courseoffering_name':
                       smart_text(course_offering.course),
                       'courseoffering_news_name':
                       notification.course_offering_news.title,
                       'courseoffering_news_text':
                       notification.course_offering_news.text}

            notify(notification, name, context)

        translation.deactivate()
