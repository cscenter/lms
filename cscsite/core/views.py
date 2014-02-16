from braces.views import UserPassesTestMixin

class StudentOnlyMixin(UserPassesTestMixin):
    def test_func(self, user):
        return user.is_student

class TeacherOnlyMixin(UserPassesTestMixin):
    def test_func(self, user):
        return user.is_teacher
