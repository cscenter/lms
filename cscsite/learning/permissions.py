from core.utils import is_club_site
from learning.settings import STUDENT_STATUS


class LearningPermissionsMixin(object):
    @property
    def _cached_groups(self):
        return set()

    def get_cached_groups(self):
        return self._cached_groups

    @property
    def is_student(self):
        return (self.is_student_center or
                self.is_student_club or
                self.is_volunteer)

    @property
    def is_student_center(self):
        return self.group.STUDENT_CENTER in self._cached_groups

    @property
    def is_student_club(self):
        return self.group.STUDENT_CLUB in self._cached_groups

    @property
    def is_active_student(self):
        if is_club_site():
            return self.is_student_club
        return self.is_student and self.status != STUDENT_STATUS.expelled

    @property
    def is_teacher(self):
        return self.is_teacher_center or self.is_teacher_club

    @property
    def is_teacher_club(self):
        return self.group.TEACHER_CLUB in self._cached_groups

    @property
    def is_teacher_center(self):
        return self.group.TEACHER_CENTER in self._cached_groups

    @property
    def is_graduate(self):
        return self.group.GRADUATE_CENTER in self._cached_groups

    @property
    def is_volunteer(self):
        return self.group.VOLUNTEER in self._cached_groups

    @property
    def is_master_student(self):
        """
        Studying for a masters degree. Student with this group should be
        center student or volunteer.
        """
        return self.group.MASTERS_DEGREE in self._cached_groups

    @property
    def is_curator(self):
        return self.is_superuser and self.is_staff

    @property
    def is_curator_of_projects(self):
        return self.group.CURATOR_PROJECTS in self._cached_groups

    @property
    def is_interviewer(self):
        return self.group.INTERVIEWER in self._cached_groups

    @property
    def is_project_reviewer(self):
        return self.group.PROJECT_REVIEWER in self._cached_groups
