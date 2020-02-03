from django.contrib import messages
from vanilla import TemplateView


class NotyView(TemplateView):
    template_name = "v2/components/noty.jinja2"

    def get_context_data(self, **kwargs):
        messages.warning(self.request, "<h3>Предупреждение</h3><p>Вы добавили уже 20 часов лекций в неделю, рассчитайте свои силы :)</p>")
        messages.info(self.request, "<h3>Переадресация</h3><p>Страница «Обучение» теперь стала отдельной страницей</p> <a href="">Узнать подробнее</a><span><a href="">Отменить</a></span>")
        messages.error(self.request, "<h3>Ошибка</h3>Нельзя поставить два занятия на одно и то же время")
        messages.success(self.request, "<h3>Добавлен новый пользователь</h3> Петров Олег Олегович ")
        messages.success(self.request, "Я тут повисю пару секунд, зырьте", extra_tags='timeout')
        return {}


class AlumniView(TemplateView):
    template_name = "v2/pages/alumni.jinja2"

    def get_context_data(self, **kwargs):
        app_data = {
            "state": {
                "area": self.kwargs.get("area", None),
                "branch": self.kwargs.get("branch", None),
                "year": self.kwargs.get("year", {"label": '2019', "value": 2019})
            },
            "props": {
                "endpoint": '/ajax/alumni.json',
                "branchOptions": [
                    {"label": 'Санкт-Петербург', "value": 'spb'},
                    {"label": 'Новосибирск', "value": 'nsk'}
                ],
                "areaOptions": [
                    {"label": 'Современная информатика', "value": 'cs'},
                    {"label": 'Разработка ПО', "value": 'se'},
                    {"label": 'Анализ данных', "value": 'ds'},
                ],
                "yearOptions": [{"label": str(y), "value": y} for y in reversed(range(2013, 2020))]
            }
        }
        return {
            "app_data": app_data
        }


class TeachersView(TemplateView):
    template_name = "v2/pages/teachers.jinja2"

    def get_context_data(self, **kwargs):
        app_data = {
            "state": {
                "branch": self.kwargs.get("branch", None),
            },
            "props": {
                "endpoint": '/ajax/teachers.json',
                "coursesURL": '/ajax/courses.json',
                "branchOptions": [
                    {"label": 'Санкт-Петербург', "value": 'spb'},
                    {"label": 'Новосибирск', "value": 'nsk'}
                ],
                "termIndex": 34
            }
        }
        return {
            "app_data": app_data
        }
