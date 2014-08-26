# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import csv
from datetime import date

from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail

from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.template import Template, Context
from django.utils.encoding import force_text, force_bytes
from django.utils.http import urlsafe_base64_encode

from users.models import CSCUser


EMAIL_TEMPLATE = """\
Добрый день!

Сегодня мы поздравляем Вас с началом первого учебного года в центре, хотим рассказать самое необходимое для посещения первых лекций и пригласить на первое организационное собрание.

Семестр начинается 8 сентября. Напомним, что в качестве курсов можно сдавать любые из: курсы CS центра, курсы CS клуба (семестровые или “интенсивные”), заочно курсы московского ШАД.

Для своевременного получения информации по поводу обучения в центре предлагаем Вам вступить в группу: https://groups.google.com/forum/#!forum/compscicenter2014  Индивидуальные письма более рассылаться не будут. В эту группу приходят и оповещения об отмене или переносе занятий, и анонсы общих мероприятий, и просто срочные сообщения от кураторов.

Чтобы получать актуальную информацию по конкретному курсу, нужно научиться пользоваться нашим сайтом. Для почти всех курсов там публикуется информация о занятиях, а для некоторых через него будет происходить сдача домашних заданий. На сайте нельзя зарегистрироваться самостоятельно, поэтому у каждого уже есть свой пользователь. Непосредственно ваши данные для входа:
Логин: {{ user.username }}
Ссылка на форму создания пароля: http://compscicenter.ru{% url 'password_reset_confirm' uidb64=uid token=token %}

Заполните, пожалуйста, свой профиль: добавьте ID на Stepic (если ещё не указан), логин на Яндексе и фотографию.

8 сентября пройдёт организационное собрание, на котором вы сможете больше узнать про курсы, которые будут читаться для вас в этом семестре, про то, какие есть правила обучения и поведения в центре, познакомиться с преподавателями, кураторами и другими студентами. Конечно, в этот же день мы будем рады ответить на любые ваши вопросы, которые возникнут в первую учебную неделю. Собрание пройдёт в БЦ Таймс (подробнее ниже) и начнётся в обычное для занятий время: 18:30.

Места проведения занятий указаны в расписании. Подробнее о них:
- ФМЛ 239, Кирочная, 8. Мы занимаемся в двух помещениях второго корпуса, Актовый зал и ауд. 25. Здание на карте: http://maps.yandex.ru/?um=kckPoQ0DQa3WXvwGMiEQC4Y7H1ANN3oP&ll=30.352079%2C59.944560&spn=0.010074%2C0.002573&z=17&l=map
- БЦ Таймс, Кантемировская ул, д. 2. На четвёртом этаже в нашем распоряжении две лекционные аудитории, пара аудиторий для практик и кофе и чай. http://maps.yandex.ru/-/CVvUYE9n
- ПОМИ РАН, наб. Фонтанки, 27. Занимаемся в Мраморном зале, второй этаж. http://maps.yandex.ru/?um=p_SCiFNdb8BHDBGiK-pSmzmDtOGNbJNC&ll=30.342789%2C59.933856&spn=0.010074%2C0.002574&z=17&l=map


Расписание в центре
Подробная информация о всех курсах будет опубликована к 8 сентября. Если у вас будут предложения по изменению расписания (не сможете ходить или курсы идут одновременно), пишите в ответ на это письмо или расскажите в день орг. собрания – попробуем решить проблему.

Расписание в клубе: compsciclub.ru/cur (каждый выходной оно меняется, смотрите внимательно)

Курсы ШАД: http://shad.yandex.ru
а) доступ к Wiki ШАД будет выдан всем студентам в начале сентября (в соответствии с логинами на Яндексе, указанными в ваших профилях на сайте);
б) если вы решите сдавать какой-то курс из ШАД, напишите об этом кураторам, и мы добавим вас в ведомость – без этого домашние задания проверяться не будут.

Письмо вы получили с адреса электронной почты, на который разумно писать любые вопросы к кураторам центра. Вам ответит кто-то из нас (Александр Сергеевич, Женя или Катя).

До встречи!

--
Кураторы центра
"""


class Command(BaseCommand):
    args = "path/to/students.csv path/to/stepic.csv"
    help = "Imports users from Excel CSV files"

    def handle(self, *args, **options):
        try:
            [students_path, stepic_path] = args
            with open(stepic_path, "rU") as f:
                stepic_ids = {user: int(id) for id, user in csv.reader(f)}

            with open(students_path, "rU") as f:
                r = csv.DictReader(f, ["last_name", "first_name",
                                       "middle_name",
                                       "email", "user"])
                r.next()  # skip header.
                students = list(r)
        except (ValueError, IOError):
            raise CommandError("CSV wher art thou?")

        today = date.today()
        users = []
        with transaction.atomic():
            # a) create users
            for row in students:
                print(row["email"], end=" ")
                username, domain = row["email"].split("@", 1)
                if CSCUser.objects.filter(username=username):
                    print("[skipping]")
                    continue

                stepic_id = stepic_ids.get(row["user"])
                user = CSCUser.objects.create_user(
                    username, row["email"],
                    CSCUser.objects.make_random_password(),
                    first_name=force_text(row["first_name"]),
                    last_name=force_text(row["last_name"]),
                    patronymic=force_text(row["middle_name"]),
                    enrollment_year=today.year, stepic_id=stepic_id)
                user.groups.add(CSCUser.IS_STUDENT_PK)
                users.append(user)
                print("ok")

        # b) send password reset notifications
        for user in users:
            print("emailing " + user.email, end=" ")
            context = {
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': default_token_generator.make_token(user),
            }
            email = Template(EMAIL_TEMPLATE).render(Context(context))
            send_mail("Скоро начало первого семестра в CS центре",
                      email, "curators@compscicenter.ru", [user.email])
            print("ok")








