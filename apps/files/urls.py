from django.urls import path, include

from learning.views import AssignmentAttachmentDownloadView, \
    AssignmentCommentAttachmentDownloadView

app_name = 'files'

urlpatterns = [
    path('assignments/<slug:sid>/<str:file_name>', AssignmentAttachmentDownloadView.as_view(), name='download_assignment_attachment'),
    path('assignments/comments/<slug:sid>/<str:file_name>', AssignmentCommentAttachmentDownloadView.as_view(), name='download_assignment_comment_attachment'),
]
