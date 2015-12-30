from django.apps import AppConfig
from django.core import checks
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from .signals import (maybe_upload_slides, populate_assignment_students,
                        create_deadline_change_notification,
                      populate_student_assignments,
                      create_assignment_comment_notification,
                      update_last_commented_date_on_assignment_student,
                      create_course_offering_news_notification,
                      mark_assignment_passed)

def check_learning_app_default_settings(**kwargs):
    from django.conf import settings
    errors = []
    # FIXME: Really don't know is it appropriate place or not. Maybe replace with default settings?
    if not settings.LEARNING_BASE:
        errors.extend([checks.Error(
            "'{}' setting must be specified".format("LEARNING_BASE"))])
    if not settings.TEACHING_BASE:
        errors.extend([checks.Error(
            "'{}' setting must be specified".format("TEACHING_BASE"))])
    return errors

class LearningConfig(AppConfig):
    name = 'learning'
    verbose_name = _("Learning")

    def ready(self):
        checks.register(check_learning_app_default_settings)
        post_save.connect(populate_assignment_students,
                          sender=self.get_model('Assignment'))
        post_save.connect(create_deadline_change_notification,
                          sender=self.get_model('Assignment'))
        post_save.connect(create_assignment_comment_notification,
                          sender=self.get_model('AssignmentComment'))
        post_save.connect(update_last_commented_date_on_assignment_student,
                          sender=self.get_model('AssignmentComment'))
        post_save.connect(mark_assignment_passed,
                          sender=self.get_model('AssignmentComment'))
        post_save.connect(maybe_upload_slides,
                          sender=self.get_model('CourseClass'))
        post_save.connect(create_course_offering_news_notification,
                          sender=self.get_model('CourseOfferingNews'))
        post_save.connect(populate_student_assignments,
                          sender=self.get_model('Enrollment'))
