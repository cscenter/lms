from django.contrib import messages
from django.shortcuts import redirect


class StudentCityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """City code for CS Center student is mandatory."""
        u = request.user
        if (u.is_student_center or u.is_volunteer) and not u.city_id:
            if request.path != "/":
                messages.error(request, "Для вашего профиля не указан город. "
                                        "Обратитесь к куратору.")
                return redirect(to="/")
        return self.get_response(request)
