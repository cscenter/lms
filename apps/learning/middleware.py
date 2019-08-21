from django.contrib import messages
from django.shortcuts import redirect


# FIXME: сделать отделение обязательным и удалить
class StudentBranchMiddleware:
    """
    Redirects students with non-set city code in user settings to the main
    page and shows the error with instructions how to fix it.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        u = request.user
        if (u.is_student or u.is_volunteer) and not u.branch_id:
            if request.path != "/":
                messages.error(request,
                               "Для вашего профиля не указано отделение. "
                               "Обратитесь к куратору.")
                return redirect(to="/")
        return self.get_response(request)
