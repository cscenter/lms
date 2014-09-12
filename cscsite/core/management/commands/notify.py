# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
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
           'template': "emails/new_courseoffering_news.html"}}


def notify(notification, name, context):
    if not notification.user.email:
        print ("user {0} doesn't have an email"
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
    print "sending {0} ({1})".format(smart_text(notification),
                                     smart_text(name))
    msg.send()
    notification.is_notified = True
    notification.save()


class Command(BaseCommand):
    help = 'Sends notifications through email'

    def handle(self, *args, **options):
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
            if notification.user == notification.assignment_student.student:
                name = 'new_comment_for_student'
                context = {'a_s_link':
                           ("http://compscicenter.ru/learning/assignments/{0}/"
                            .format(notification.assignment_student.pk)),
                           # reverse('a_s_detail_student',
                           #         notification.assignment_student.pk),
                           'assignment_name':
                           smart_text(notification.assignment_student)}
            else:
                student = notification.assignment_student.student

                name = 'new_comment_for_teacher'
                context = {'student_name': smart_text(student),
                           'a_s_link':
                           # FIXME: reverse doesn't work in management,
                           # investigate, hardcode for now
                           ("http://compscicenter.ru/"
                            "teaching/assignments/submissions/{0}/"
                            .format(notification.assignment_student.pk)),
                           # reverse('a_s_detail_teacher',
                           #         notification.assignment_student.pk),
                           'assignment_link':
                           ("http://compscicenter.ru/teaching/assignments/{0}/"
                            .format(notification.assignment_student
                                    .assignment.pk)),
                           # reverse('assignment_detail_teacher',
                           #         notification.assignment_student
                           #         .assignment.pk),
                           'assignment_name':
                           smart_text(notification.assignment_student)}

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
