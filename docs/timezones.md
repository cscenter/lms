### Особенности работы с таймзонами

Postgres хранит datetime как ::timestamptz, который перед сохранением конвертирует время в UTC, а возвращая - с учетом настроек соединения. 
Некоторые примеры поведения postgres можно увидеть разделом ниже, но по сути всю работу с часовыми поясами делает приложение, 
поэтому стоит сосредоточиться на поведении Django. 

```
In [1]: with connection.cursor() as cursor:
    cursor.execute('show timezone')
    row = cursor.fetchone()

In [2]: row
Out[2]: ('UTC',)
# Т.е. промежуточных конвертаций при перегоне дат из приложения в БД и обратно у нас нет. Django просто создаёт aware-объект c `tzinfo=UTC`. 
Postgres получает и отдаёт UTC метку.
```



   
Python поддерживает `tzinfo` для `time`, но Django тип `time` всегда хранит как naive и ничего не знает о часовом поясе. Postgres придерживается такого же мнения. 
Что насчёт `datetime`?

В настройках приложения выставлено `USE_TZ=True`, поэтому Django внутри использует timezone-aware объекты, где `tzinfo=pytz.UTC`. 
Например, утилита `django.utils.timezone.now`, которая используется для получения текущего времени, 
возвращает aware-объект - берётся UNIX-время сервера (согласовано с UTC) и добавляется информация с таймзоной.

По идее, мы всегда должны работать с aware-объектами на уровне приложения, иначе нельзя производить операции взятия разницы 
между объектами datetime (python просто не даст это сделать и выкинет ошибку), но могут возникать ситуации, 
когда мы работаем с naive объектом, который пытаемся сохранить в БД. 
Django в этом случае в лог пишет warning, добавляет к naive объекту таймзону, указанную в `TIME_ZONE`, делая его aware. 
Таймзона по-умолчанию это мск, поэтому если naive объект содержит время из Нск, то могут возникнуть некоторые проблемы в дальнейшем. 
Например, мы будем невовремя отправлять уведомление, ошибаясь при проверке, наступило ли время отправки. 
Rule of thumb - избавляться от всех warning'ов `received a naive datetime`. При преобразовании naive -> aware учитывать часовой пояс.
При этом есть важный момент, про который стоит знать и который нужно учитывать. 
Нельзя в лоб использовать метод `datetime.replace` для корректировки часового пояса в naive-объектах.
Дело в том, что он будет по-глупому использовать первую запись из tz data source. Пример такого источника:

```
# Zone  NAME            GMTOFF   RULES       FORMAT   [UNTIL]
Zone    Europe/Berlin   0:53:28  -           LMT      1893 Apr
                        1:00     C-Eur       CE%sT    1945 May 24 2:00
                        1:00     SovietZone  CE%sT    1946
                        1:00     Germany     CE%sT    1980
                        1:00     EU          CE%sT
```

С учетом структуры выше, рассмотрим как будет работать `replace`:

```
import pytz
from datetime import datetime
tz = pytz.timezone('Europe/Berlin')

>>> tz
<DstTzInfo 'Europe/Berlin' LMT+0:53:00 STD>

dt = datetime(2011, 1, 3, 18, 40)
result = tz.localize(dt)

>>> result.tzinfo
<DstTzInfo 'Europe/Berlin' CET+1:00:00 STD>

>>> dt.replace(tzinfo=tz)
datetime.datetime(2011, 1, 3, 18, 40, tzinfo=<DstTzInfo 'Europe/Berlin' LMT+0:53:00 STD>)

>>> result.tzinfo == tz
False
```

Т.е. как вывод - нужно использовать метод `localize`.

Всегда использовать `normalize` после арифметики с датами.

TODO: Ещё один пример возникающих проблем - создаём комментарий из Нск, на сайте отображаем дату создания - получаем время по МСК. Будет путать. 

TODO: Пока стратегия следующая - https://github.com/cscenter/site/issues/444 Если покажет свою жизнеспособность, то можно сюда перенести.
   
https://habrahabr.ru/post/273177/
https://habrahabr.ru/company/mailru/blog/242645/
http://asvetlov.blogspot.ru/2011/02/date-and-time.html


Рассмотрим ситуацию, когда можно схлопотать проблем (на примере создания interview из потока и слота):

* Берём stream.date и slot.time (время пусть будет 15:30). Они оба naive
* Цепляем их при помощи datetime.combine, получаем тоже naive-объект.
* Передаем его в форму InterviewForm. Она делает объект aware, но просто подставив tzinfo с московским часовым поясом, само время никак не меняет (dt.replace(tzinfo=tzmsk))
* Вызываем interview.date.strftime("%H:%M"). Получим 15:30
* Сохраняем собеседование. В БД получаем запись примерно как 2017-06-26 15:30:00+03. 
* В шаблонах эта дата показывается как 15:30, т.е. Django учтёт часовой пояс из настроек
* Получим сохранённую модель из БД. interivew = Interview.objects.get(...). 
* Заново вызовем interview.date.strftime("%H:%M") Значение уже 12:30... Postgres хранит дату как UTC, получаем из БД тоже UTC, а это уже 12:30

Мораль - перед тем как пользоваться strftime, нужно учесть часовой пояс. Более общее утверждение - перед форматированием учесть часовой пояс.

Если хочется, чтобы postgres возвращал всё в UTC, нужно выполнить `SET SESSION timezone TO 'UTC';` для текущей сессии.

   
### Некоторые особенности работы postgres с датами

```
cscdb=> select '2014-04-04 20:00:00'::timestamptz;
      timestamptz
------------------------
 2014-04-04 20:00:00+04
(1 row) -- PG считает, что передано время без учета часового пояса. Берёт таймзону текущего соединения, на его основе конвертирует время в UTC. А выводит местное, с добавлением информации о часовом поясе, в котором отображает.

cscdb=> select '2014-04-04 20:00:00'::timestamptz at time zone 'UTC';
      timezone
---------------------
 2014-04-04 16:00:00
(1 row) -- как PG покажет время, если `show timezone` показывает пояс для UTC+0

cscdb=> select '2014-04-04 20:00:00'::timestamp;
      timestamp
---------------------
 2014-04-04 20:00:00
(1 row) -- Не показывает информацию о поясе, как и положено

cscdb=> select '2014-04-04 20:00:00'::timestamp at time zone 'UTC';
        timezone
------------------------
 2014-04-05 00:00:00+04
(1 row) -- В зоне UTC было 20:00, а наше местное на 4 часа больше. Его мы и видим.
```

### Как python отображает даты в консоли:

Из кода ниже можно сделать вывод, что время показывается локализованное (с учетом часового пояса).

```
# Naive
In [1]: datetime(2017, 6, 26, 0, 0)
Out[1]: datetime.datetime(2017, 6, 26, 0, 0)

# Aware with UTC timezone
In [2]: datetime(2017, 6, 26, 0, 0, tzinfo=pytz.UTC)
Out[2]: datetime.datetime(2017, 6, 26, 0, 0, tzinfo=<UTC>)

# Incorrect aware with MSK timezone (call `normalize` to fix)
In [3]: datetime(2017, 6, 26, 0, 0, tzinfo=tz_msk)
Out[3]: datetime.datetime(2017, 6, 26, 0, 0, tzinfo=<DstTzInfo 'Europe/Moscow' LMT+2:30:00 STD>)

# Correct aware with MSK timezone
In [4]: tz_msk.localize(datetime(2017, 6, 26, 0, 0))
Out[4]: datetime.datetime(2017, 6, 26, 0, 0, tzinfo=<DstTzInfo 'Europe/Moscow' MSK+3:00:00 STD>)

# Convert previous datetime to UTC timezone
In [5]: tz_msk.localize(datetime(2017, 6, 26, 0, 0)).astimezone(pytz.UTC)
Out[5]: datetime.datetime(2017, 6, 25, 21, 0, tzinfo=<UTC>)
```


### TODO: Как быть с датами в админке Django

Рассмотрим все уровни, на которых у нас есть возможность корректировать таймзону:

* уровень поля/виджета формы
* уровень формы
* уровень модели

Поле формы (а значит и виджет) ничего не знает о модели, с которой он работает, значит нужно как минимум кастомизировать ещё форму.
Если логику разместить на уровне модели, то это только добавит сложности, поскольку формы никто не отменял и нужно будет их кастомизировать. 
Вариант с отключением USE_TZ=False не подходит, поскольку есть ещё даты, которые генерируются автоматом в UTC и терять этот механизм не хочется.
TODO: убедиться, что автоматом создаваемые поля не подвергаются изменениям

1. **Отображение формы**. 

Django любое поле datetime по-умолчанию показывает с помощью `django.contrib.admin.widgets.AdminSplitDateTime`.
Это wrapper над `django.forms.widget.SplitDateTimeWidget`, вся логика над датами лежит там. Нас интересует метод `decompress`, 
который разбивает значения `datetime` на составляющие [date, time]. Внутри он использует следующий метод

```
def decompress(self, value):
    if value:
        value = to_current_timezone(value)
        return [value.date(), value.time().replace(microsecond=0)]
    return [None, None]
        
        
def to_current_timezone(value):
    """
    When time zone support is enabled, convert aware datetimes
    to naive datetimes in the current time zone for display.
    """
    if settings.USE_TZ and value is not None and timezone.is_aware(value):
        current_timezone = timezone.get_current_timezone()
        return timezone.make_naive(value, current_timezone)
    return value
```

`make_naive` сначала локализует время до `current_timezone`, а затем убивает информацию о таймзоне (устанавливает `tzinfo=None`)

Получается, на отображение времени в форме админки будет влиять выставленная таймзона (встроенный механизм Django для дат), поэтому необходимо кастомизировать виджет.


2. **Обработка формы**. 

* Создаём форму на основе POST-данных
* Валидируем данные, вызываем `is_valid`:

    * Если `empty_permitted=True`, то сперва убедимся, что есть измененные данные (сформируем `changed_data`). 
    Если их нет, то завершим вызов `full_clean`.
    Как формируется `changed_data`:
        Для каждого поля формы вызывается метод `has_changed`, 
        этому методу передаются текущее значение поля (initial) и новое (data), они сравниваются. 
        Для любого поля datetime в админке данные приходят раздельно, поэтому они сперва склеиваются методом `field.compress` : [date, time] -> datetime
    Если вызов `changed_data` произошёл когда `empty_permitted=True`, то методы `compress` и `decompress` будут использовать старое (т.е. текущее) значение таймзоны. 
    Ещё надо отметить, что `empty_permitted=True` внутри Django только для `formsets`, т.е. вероятность, что `changed_data` сформируется здесь - крайне мала
    TODO: Попробовать избежать зависимости от `changed_data`, т.к. поведение недетерминировано!
    * Очищается каждое поле по отдельности (формируем `cleaned_data`). Надо учитывать, что `cleaned_data` сформируется 
    до обновления данных модели, т.е. таймзона ещё не обновлена на этот момент. А именно значения из `cleaned_data` запишутся в БД.
    * Вызывается метод `.clean()` для всей формы целиком
    * Вызывается _post_clean(), который устанавливает новые значения для модели (на основе `cleaned_data`)

* Если данные валидны (form.errors пуст), то сохраняем объект в БД (Вызовы `.save_form()` и `.save_model()`)
* Вызываем `changed_data` для формирования JSON, какие данные были изменены. Если это первый 
вызов `changed_data`, то на этом этапе модель уже имеет обновленные значения.

3. **Как подключить**

3.1 В `ModelAdmin` надо добавить:

```
from core.admin import CityAwareModelForm, BaseCityAwareSplitDateTimeWidget, \ 
    CityAwareSplitDateTimeField
form = CityAwareModelForm
formfield_overrides = {
    models.DateTimeField: {
        'widget': BaseCityAwareSplitDateTimeWidget,
        'form_class': CityAwareSplitDateTimeField
    }
}
```

`CityAwareModelForm` в каждый виджет `BaseCityAwareSplitDateTimeWidget` прокинет 
ссылку на текущий инстанс модели, чтобы при вызове метода `decompress` 
(datetime -> [date, time]) можно было учесть часовой пояс.

У `CityAwareSplitDateTimeField` метод `compress` ([date, time] -> datetime) 
также умеет учитывать часовой пояс.

3.2 У модели должны быть реализованы 2 метода:

```
def get_timezone(self) -> datetime.tzinfo:
    # 
    pass

@property
def city_aware_field_name(self):
    # Если field_name в `changed_data` при изменении модели - пересчитаем 
    # время в UTC с учетом нового часового пояса. 
    # Это нужно сделать, поскольку `cleaned_data` формируется до обновления 
    # данных у текущего инстанса модели.
    pass
``` 


### Ограничения:

* При создании модели вручную, надо самим учитывать часовой пояс
* Если есть цепочка зависимостей foo -> bar -> baz -> venue -> city, то поле `foo.deadline_at`, 
значение которого зависит от часового пояса, не будет пересчитано, если таймзону поменяли через изменение значения `bar.baz`, а не `foo.bar`.
* Фильтр по дате в списке собеседований работает не совсем корректно, т.к. формируется запрос 
`BETWEEN '2017-07-20T00:00:00+00:00'::timestamptz AND '2017-07-21T00:00:00+00:00'::timestamptz`. 
Учитывая, что даты хранятся как метки UTC, мы можем получить фильтр по неверной дате (т.к. указывают локальную дату). Это не совсем проблема, т.к. раньше 7 утра 
собеседований точно не может быть, но идеально было бы вообще выпилить общий список (где идут все собеседования из СПб и Нск подряд)
* Нельзя избавиться от formfield_overrides в настройках ModelAdmin, хотя мы и используем кастомную форму, т.к. на уровне формы можно менять form_classes/widgets только конкретных полей (указанием их имён).
Пропатчить mapping django.contrib.admin.options.FORMFIELD_FOR_DBFIELD_DEFAULTS не получится (в методе core.apps.ready), т.к. классы собираются в django.contrib.admin.apps.ready, 
который вызывается раньше нашего core приложения (возможности подключить core приложение раньше админки нет из-за зависимости от django.contrib.site и других)

TODO:

* спрятать предупреждение `Внимание: Ваше локальное время опережает время сервера на 3 часа.`
