from django.urls import path, include

from . import views as v

app_name = 'learning-api'

urlpatterns = [
    path('v1/', include(([
        path('teaching/assignments/progress/<int:pk>/', v.StudentAssignmentUpdate.as_view(), name='student_assignment_update'),
    ], 'v1')))
]
