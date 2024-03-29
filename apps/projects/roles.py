from djchoices import C, DjangoChoices

from django.utils.translation import gettext_lazy as _

from auth.permissions import Role
from auth.registry import role_registry

from .permissions import (
    UpdateOwnReportComment, UpdateReportComment, ViewProjectsMenu, ViewReportAttachment,
    ViewReportAttachmentAsReviewer, ViewReportCommentAttachment,
    ViewReportCommentAttachmentAsReviewer
)


class Roles(DjangoChoices):
    PROJECT_REVIEWER = C(9, _('Project reviewer'), permissions=(
        ViewProjectsMenu,
        UpdateOwnReportComment,
        ViewReportAttachmentAsReviewer,
        ViewReportCommentAttachmentAsReviewer,
    ))
    CURATOR_PROJECTS = C(10, _('Curator of projects'), permissions=(
        ViewProjectsMenu,
        UpdateReportComment,
        ViewReportAttachment,
        ViewReportCommentAttachment,
    ))


for code, name in Roles.choices:
    role_registry.register(Role(id=code, code=code, description=name,
                                permissions=Roles.get_choice(code).permissions))


reviewer_role = role_registry[Roles.PROJECT_REVIEWER]
reviewer_role.add_relation(UpdateReportComment, UpdateOwnReportComment)
reviewer_role.add_relation(ViewReportAttachment, ViewReportAttachmentAsReviewer)
reviewer_role.add_relation(ViewReportCommentAttachment,
                           ViewReportCommentAttachmentAsReviewer)
