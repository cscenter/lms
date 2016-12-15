from django.apps import AppConfig
from django.db.models.signals import post_save, post_init
from django.utils.translation import ugettext_lazy as _



class LearningConfig(AppConfig):
    name = 'learning'
    verbose_name = _("Learning")

    def ready(self):
        from .signals import (create_student_assignments_for_new_assignment,
                              create_deadline_change_notification,
                              populate_assignments_for_new_enrolled_student,
                              assignment_comment_post_save,
                              create_course_offering_news_notification,
                              track_fields_post_init,
                              add_upload_slides_job)
        post_save.connect(create_student_assignments_for_new_assignment,
                          sender=self.get_model('Assignment'))
        post_save.connect(create_deadline_change_notification,
                          sender=self.get_model('Assignment'))
        # FIXME: redesign with `from_db` method!
        post_init.connect(track_fields_post_init,
                          sender=self.get_model('CourseClass'),
                          dispatch_uid='learning.signals.course_class_post_init')
        post_save.connect(add_upload_slides_job,
                          sender=self.get_model('CourseClass'),
                          dispatch_uid='learning.signals.course_class_add_upload_slides_job')
        post_save.connect(create_course_offering_news_notification,
                          sender=self.get_model('CourseOfferingNews'))
        post_save.connect(populate_assignments_for_new_enrolled_student,
                          sender=self.get_model('Enrollment'))
