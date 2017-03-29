from django.db.models import query, Manager, Prefetch



class StudentAssignmentQuerySet(query.QuerySet):
    def for_user(self, user):
        related = ['assignment',
                   'assignment__course_offering',
                   'assignment__course_offering__course',
                   'assignment__course_offering__semester']
        return (self
                .filter(student=user)
                .select_related(*related)
                .order_by('assignment__course_offering__course__name',
                          'assignment__deadline_at',
                          'assignment__title'))

    def in_term(self, term):
        return self.filter(assignment__course_offering__semester_id=term.id)


class StudyProgramQuerySet(query.QuerySet):
    def syllabus(self):
        from learning.models import StudyProgramCourseGroup
        return (self.select_related("area")
                    .prefetch_related(
                        Prefetch(
                            'course_groups',
                            queryset=(StudyProgramCourseGroup
                                      .objects
                                      .prefetch_related("courses")),
                        )))
