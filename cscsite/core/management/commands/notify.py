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
from index.models import EnrollmentApplEmail

# import cscenter.urls

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


def get_base_url(notification):
    user = notification.user
    if isinstance(notification, AssignmentNotification):
        co = notification.student_assignment.assignment.course_offering
    elif isinstance(notification, CourseOfferingNewsNotification):
        co = notification.course_offering_news.course_offering
    else:
        raise NotImplementedError()
    if not user.is_student_center:
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


# FIXME: investigate and delete legacy code
def notify_enrollment_appl(application, context, f):
    name = 'enrollment_application'

    rendered_str = render_to_string(EMAILS[name]['template'], context)
    html_content = linebreaks(rendered_str)
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(EMAILS[name]['title'],
                                 text_content,
                                 settings.DEFAULT_FROM_EMAIL,
                                 [application.email])
    msg.attach_alternative(html_content, "text/html")
    report(f, "sending {0} ({1})".format(smart_text(application),
                                         smart_text(name)))
    msg.send()
    application.is_notified = True
    application.save()


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
                       'a_s_created':
                       a_s.created,
                       'assignment_name':
                       smart_text(a_s.assignment),
                       'assignment_text':
                       smart_text(a_s.assignment.text),
                       'student_name':
                       smart_text(a_s.student),
                       'deadline_at':
                       a_s.assignment.deadline_at,
                       'course_name':
                       smart_text(a_s.assignment.course_offering.course)}
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
                           base_url
                           + reverse('course_offering_detail',
                                 args=[course_offering.course.slug,
                                       course_offering.semester.slug]),
                       'courseoffering_name':
                       smart_text(course_offering.course),
                       'courseoffering_news_name':
                       notification.course_offering_news.title,
                       'courseoffering_news_text':
                       notification.course_offering_news.text,
                       'course_name':
                       smart_text(course_offering.course)}

            notify(notification, name, context, self.stdout)
        # FIXME: looks like I have to delete this legacy code!
        enrollment_applications = (EnrollmentApplEmail.objects
                                   .filter(is_notified=False))
        for ea in enrollment_applications:
            notify_enrollment_appl(ea, {}, self.stdout)

        translation.deactivate()
