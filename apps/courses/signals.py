from typing import Set

from django.db.models.signals import m2m_changed, pre_save
from django.dispatch import receiver

from core.models import Branch
from courses.models import Course, CourseBranch
from learning.services import StudentGroupService


# FIXME: post_delete - если удаляется главная бранча, то запретить (лучше в админке?) 2. Убедиться, что она всегда есть, видимо, тоже в админке? Если на Course.post_add, то может быть ошибка валидации.
def manage_course_branches(sender, **kwargs):
    action = kwargs.pop("action")
    if action not in ("pre_add", "post_remove"):
        return
    course = kwargs.pop("instance")
    branches: Set[int] = kwargs.pop("pk_set", set())
    for branch_id in branches:
        # Case when the main branch was added as an additional one
        if branch_id == course.main_branch_id:
            continue
        branch = Branch.objects.get_by_pk(branch_id)
        if action == "post_add":
            StudentGroupService.add(course, branch)
        elif action == "post_remove":
            StudentGroupService.remove(course, branch)
