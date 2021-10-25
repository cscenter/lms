### Токен авторизации

Все запросы к API должны содержать заголовок `Authorization: Token <auth_token>`, 
где `<auth_token>` - токен авторизации, его можно получить с помощью запроса:

```python
import requests
LMS_DOMAIN = 'http://my.csc.test'
GET_TOKEN_ENDPOINT = f'{LMS_DOMAIN}/api/v1/token/'
response = requests.post(GET_TOKEN_ENDPOINT, data={'login':'email@example.com', 'password': '123123'})
auth_token = response.json()['secret_token']
```

В ответе запроса, если данные аккаунта были указаны верно, содержится токен авторизации.
Токена сейчас бессрочный, но в будущем время жизни может быть ограничено текущим семестром.

### Список курсов

```python
import requests
LMS_DOMAIN = 'http://my.csc.test'
COURSE_LIST = f'{LMS_DOMAIN}/api/v1/teaching/courses/'
auth_token = 'XXXXXXXXXX'
response = requests.get(COURSE_LIST, headers={'Authorization': f'Token {auth_token}'})
"""
Пример ответа:
[
    {
        'id': 9,  # это идентификатор курса, его можно использовать для получения списка заданий или студентов
        'name': 'Основы программирования',
        'url': '/courses/2020-autumn/2.9-programming_basics/',
        'semester': {
            'id': 1,
            'index': 122,
            'year': 2020,
            'academic_year': 2020,
            'type': 'autumn'
        }
    },
    ...
]
"""
```

### Список студентов курса

```python
import requests
LMS_DOMAIN = 'http://csc.test'
course_id = 9
ENROLLMENT_LIST = f'{LMS_DOMAIN}/api/v1/teaching/courses/{course_id}/enrollments/'
auth_token = 'XXXXX'
response = requests.get(ENROLLMENT_LIST, headers={'Authorization': f'Token {auth_token}'})

"""
Пример ответа
response.json()
[
    {
        'id': 20,  # идентификатор студента, уникальный в рамках курса
        'grade': 'not_graded',
        'studentGroupId': 1595,
        'student': {
            'id': 122,
            'firstName': 'Иван',
            'lastName': 'Иванов',
            'patronymic': 'Иванович'
        },
        'studentProfileId': 12443
    },
    {
        'id': 205,
        'grade': 'not_graded',
        'studentGroupId': 1595,
        'student': {
            'id': 153,
            'firstName': 'Антон',
            'lastName': 'Антонов',
            'patronymic': 'Антонович'
        },
        'studentProfileId': 12443
    },
    ...
]
"""
```

### Список занятий курса

```python
import requests

LMS_DOMAIN = 'http://csc.test'
course_id = 9
auth_token = 'XXXXXXX'
endpoint = f'{LMS_DOMAIN}/api/v1/teaching/courses/{course_id}/assignments/'
response = requests.get(endpoint, headers={'Authorization': f'Token {auth_token}'})
"""
[
    {
        "id": 2727,
        "deadlineAt": "2021-10-22T20:00:00Z",
        "title": "Homework #3",
        "passingScore": 2,
        "maximumScore": 5,
        "weight": "1.00",
        "ttc": null,
        "solutionFormat": "external"
    },
    {
        "id": 2728,
        "deadlineAt": "2021-10-22T20:00:00Z",
        "title": "Homework #3 (ИТМО)",
        "passingScore": 2,
        "maximumScore": 5,
        "weight": "1.00",
        "ttc": null,
        "solutionFormat": "external"
    },
    ...
]
"""
```

### Выставление оценки

FIXME: нужно переделать endpoint на использование enrollmentId (идентификатор студента в рамках курса)
TODO: Можно апдейтить оценку за задание с помощью методов put/patch, отправляем json. В случае успеха вернётся 200й код ответа, 400 - если ошибка валидации
TODO: Добавить пример с ошибкой валидации

```python
import requests

LMS_DOMAIN = 'http://csc.test'
course_id = 9
assignment_id = 2727
enrollment_id = 20
auth_token = 'XXXXXXX'
endpoint = f'{LMS_DOMAIN}/api/v1/teaching/courses/{course_id}/assignments/{assignment_id}/students/{enrollment_id}/'
response = requests.put(endpoint, json={'score': '2'}, headers={'Authorization': f'Token {auth_token}'})
assert response.status_code == 200
"""
Пример успешного ответа:
{'pk': 956, 'score': '2.00', 'state': 'pass', 'student_id': 122}
"""
```
