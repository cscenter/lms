from braces.views import UserPassesTestMixin

# FIXME: remove

class TeacherOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_teacher or user.is_curator


class ProjectReviewerGroupOnlyMixin(UserPassesTestMixin):
    """Curator must have this group"""
    raise_exception = False

    def test_func(self, user):
        return user.is_project_reviewer or user.is_curator


class StudentOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_active_student or user.is_curator


class CuratorOnlyMixin(UserPassesTestMixin):
    raise_exception = False

    def test_func(self, user):
        return user.is_curator
