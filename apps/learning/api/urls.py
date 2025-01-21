from django.urls import include, path

from . import views as v

app_name = 'learning-api'

urlpatterns = [
    path('v1/', include(([
        path('teaching/', include([
            path('courses/', v.CourseList.as_view(), name='my_courses'),
            path('courses/<int:course_id>/assignments/', v.CourseAssignmentList.as_view(), name='course_assignments'),
            path('courses/<int:course_id>/enrollments/', v.CourseStudentsList.as_view(), name='course_enrollments'),
            path('courses/<int:course_id>/personal-assignments/', v.PersonalAssignmentList.as_view(), name='personal_assignments'),
            path('courses/<int:course_id>/personal-assignments/active', v.ActivePersonalAssignmentList.as_view(), name='active_personal_assignments'),
            path('courses/<int:course_id>/assignments/<int:assignment_id>/students/<int:student_id>/', v.StudentAssignmentUpdate.as_view(), name='my_course_student_assignment_update'),
            path('courses/<int:course_id>/assignments/<int:assignment_id>/students/<int:student_id>/assignee', v.StudentAssignmentAssigneeUpdate.as_view(), name='my_course_student_assignment_assignee_update'),
        ]))
    ], 'v1')))
]
