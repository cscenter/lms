from django.urls import path, include

from . import views as v

app_name = 'learning-api'

urlpatterns = [
    path('v1/', include(([
        path('teaching/', include([
            path('courses/', v.CourseList.as_view(), name='my_courses'),
            path('courses/<int:course_id>/assignments/', v.CourseAssignmentList.as_view(), name='my_course_assignments'),
            path('courses/<int:course_id>/enrollments/', v.EnrollmentList.as_view(), name='my_course_enrollments'),
            # path('courses/<int:course_id>/assignments/<int:assignment_id>/students/', v.StudentAssignmentList.as_view(), name='my_course_student_assignments'),
            path('courses/<int:course_id>/assignments/<int:assignment_id>/students/<int:student_id>/', v.StudentAssignmentUpdate.as_view(), name='my_course_student_assignment_update'),
        ]))
    ], 'v1')))
]
