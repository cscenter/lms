from rules import always_true

from auth.permissions import all_permissions, add_perm

# Override permissions to meet compsciclub.ru requirements
assert "learning.can_view_course_news" in all_permissions
all_permissions.remove_rule("learning.can_view_course_news")

add_perm("learning.can_view_course_news", always_true)
