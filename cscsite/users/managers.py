from __future__ import unicode_literals, absolute_import

from django.contrib.auth.models import UserManager
from django.db.models import Prefetch, Count, query


class CSCUserQuerySet(query.QuerySet):
    _lexeme_trans_map = dict((ord(c), None) for c in '*|&:')

    def _form_name_tsquery(self, qstr):
        if qstr is None or not (2 < len(qstr) < 100):
            return
        lexems = []
        for s in qstr.split(' '):
            lexeme = s.translate(self._lexeme_trans_map).strip()
            if len(lexeme) > 0:
                lexems.append(lexeme)
        if len(lexems) > 3:
            return
        return " & ".join("{}:*".format(l) for l in lexems)

    def search_names(self, qstr):
        qstr = qstr.strip()
        tsquery = self._form_name_tsquery(qstr)
        if tsquery is None:
            return self.none()
        else:
            return (self
                    .extra(where=["to_tsvector(first_name || ' ' || last_name) "
                                  "@@ to_tsquery(%s)"],
                           params=[tsquery])
                    .exclude(first_name__exact='',
                             last_name__exact=''))

    def search(self, request=False):
        """Search by predefined query field list. Returns empty query_set if no
           filter parameters defined
        """
        qs = self
        filtered = False

        if request:
            # FIXME: Mb should rewrite with django-filter app
            name_qstr = request.GET.get('name', "")
            if len(name_qstr.strip()) > 0:
                qs = qs.search_names(name_qstr)
                filtered = True

            enrollemnt_years = request.GET.getlist('enrollment_years')
            eys = [int(x) for x in enrollemnt_years]
            if len(eys) > 0:
                qs = qs.filter(enrollment_year__in=eys)
                filtered = True

        return qs if filtered else qs.none()

    def students_info(self, only_will_graduate=False):
        """Returns list of students with all related courses, shad-courses
           practices and projects, etc"""

        from .models import CSCUser
        from learning.models import Enrollment, CourseClass, StudentProject

        q = self.filter(
                groups__in=[CSCUser.group_pks.STUDENT_CENTER,
                            CSCUser.group_pks.GRADUATE_CENTER]
            )
        if only_will_graduate:
            q = q.filter(status=CSCUser.STATUS.will_graduate)
        return (q
            .order_by('last_name', 'first_name')
            .prefetch_related(
                Prefetch(
                    'enrollment_set',
                    queryset=Enrollment.objects
                        .exclude(grade__in=['not_graded', 'unsatisfactory'])
                        .select_related('course_offering',
                                        'course_offering__semester',
                                        'course_offering__course'
                                        )
                        .order_by('course_offering__course__name'),
                    to_attr='enrollments'
                ),
                Prefetch(
                    'enrollments__course_offering__courseclass_set',
                    queryset=CourseClass.objects.annotate(Count('pk')),
                ),
                Prefetch(
                    'enrollments__course_offering__teachers',
                ),
                # FIXME: For some reasons semesters prefetched two times
                Prefetch(
                    'studentproject_set',
                    queryset=StudentProject.objects.order_by('project_type')
                             .prefetch_related('semesters'),
                    to_attr='projects'
                ),
                Prefetch(
                    'study_programs',
                ),
                Prefetch(
                    'shadcourserecord_set',
                    to_attr='shads'
                ),
                Prefetch(
                    'onlinecourserecord_set',
                    to_attr='online_courses'
                ),
            )
        )


class CustomUserManager(UserManager.from_queryset(CSCUserQuerySet)):
    use_in_migrations = False
