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
                "city": self.kwargs.get("city", None),
                "year": self.kwargs.get("year", {"label": '2019', "value": 2019})
            },
            "props": {
                "entry_url": '/ajax/alumni.json',
                "cities": [
                    {"label": 'Санкт-Петербург', "value": 'spb'},
                    {"label": 'Новосибирск', "value": 'nsk'}
                ],
                "areas": [
                    {"label": 'Современная информатика', "value": 'cs'},
                    {"label": 'Разработка ПО', "value": 'se'},
                    {"label": 'Анализ данных', "value": 'ds'},
                ],
                "years": [{"label": y, "value": y} for y in reversed(range(2013, 2020))]
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
                "query": self.kwargs.get("area", ""),
                "city": self.kwargs.get("city", None),
            },
            "props": {
                "entry_url": '/ajax/teachers.json',
                "courses_url": '/ajax/courses.json',
                "cities": [
                    {"label": 'Санкт-Петербург', "value": 'spb'},
                    {"label": 'Новосибирск', "value": 'nsk'}
                ],
                "term_index": 34
            }
        }
        return {
            "app_data": app_data
        }
