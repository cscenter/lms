### Delete Project in Gerrit

```bash
# delete .git folder inside gerrit app folder /data/gerrit/git/
ssh -p 29418 admin@review.compscicenter.ru gerrit flush-caches --cache projects
# TODO: run gc?
```

### Инициализация проекта для курса

Убедиться, что для преподавателей и студентов созданы ldap-аккаунты:

```python
from users.ldap import *
from django.conf import settings
import datetime
today = datetime.datetime.now().strftime('%d%m%y')
file_path = settings.ROOT_DIR / f"{today}.ldif"
# Save dump into repository root dir
export(file_path=file_path, domain_component="dc=review,dc=compscicenter,dc=ru")
```

```bash
scp <FILE_PATH> ubuntu@review.compscicenter.ru:/home/ubuntu/
ssh ubuntu@review.compscicenter.ru
ldapadd -H ldap:// -x -D "cn=admin,dc=review,dc=compscicenter,dc=ru" -w "C7G92?V6;c3M4.]e}k(Us33]" -f <TODAY>.ldif -c
```

Далее

```python
from learning.gerrit import *
from learning.models import Course
course_id = 1
course = Course.objects.get(pk=course_id)
init_project_for_course(course)
```


### Mark PatchSet as Work In Progress

```
git push origin HEAD:refs/for/master%wip
git push origin HEAD:refs/for/master%ready
```


### Copy All-Projects configuration

```bash
git clone ssh://admin@review.compscicenter.ru:29418/All-Projects.git
cd All-Projects.git
git pull origin refs/meta/config
git push origin HEAD:refs/meta/config
```

### Edit project configuration (example: add new label)
```bash
git clone ssh://admin@review.compscicenter.ru:29418/<PROJECT_NAME>.git
git fetch origin refs/meta/config:refs/remotes/origin/meta/config
git checkout meta/config
```
Edit project.config
```
[label "Verified"]
        function = MaxWithBlock
        value = -1 Fails
        value =  0 No score
        value = +1 Verified
        copyAllScoresIfNoCodeChange = true
        defaultValue = 0
[access "refs/heads/*"]
        label-Verified = -1..+1 group Non-Interactive Users
```
Make sure target group in a `groups` file (UUID can be viewed in gerrit UI)
```text
e88b5ea24c4f9488b8908632c03bf517e0707474	Non-Interactive Users
```
Now save changes
```bash
git commit -a -m "Added label - Verified"
git push origin meta/config:meta/config
```
You may need to fix author and committer
```bash
git -c "user.name=admin" -c "user.email=webmaster@compscicenter.ru" commit --amend --reuse-message=HEAD --author="admin <webmaster@compscicenter.ru>"
```


### Update gerrit user

```bash
ssh -p 29418 admin@review.compscicenter.ru gerrit set-account --delete-ssh-key 'ALL' 1000080
cat ~/.ssh/jenkins_user.pub | ssh -p 29418 admin@review.compscicenter.ru gerrit set-account --add-ssh-key - 1000080
```

## Для студента

Чтобы успешно отправлять решения в систему code review, нужно знать, как работать с ssh клиентом на вашей платформе и уметь пользоваться git.

### Обозначения:

`<USERNAME>` - логин на сайте https://review.compscicenter.ru/. Возьмите ваш email на главном сайте CS центра и замените `@` на `.`, получите логин в системе ревью.
Например, если ваша почта `student@yandex.ru`, то логин в системе ревью - `student.yandex.ru`.

`Change` - аналог Pull Request на github.com или Merge Request на gitlab.com. В рамках `Change` ведётся обсуждение отправленного кода, каждый `Change` имеет уникальный `Change-Id`.

`Change-Id` - SHA1, который вы добавляете последним абзацем в сообщение коммита (`Change-Id: <SHA1>`). 
По нему система ревью сможет связывать ваш `Patch Set` с `Change` или создать новый `Change`, если `Change-Id` из коммита ещё не зарегистрирован в системе.

`Patch Set` - история изменений в рамках `Change`. При создании `Change` у вас автоматически будет создан Patch Set 1. 
Когда вас попросят доработать код, не нужно создавать новый `Change`, нужно отправить изменения в существующий 
(ваш коммит должен содержать тот же самый Change-Id, что и ранее), такие изменения получат следующий порядковый номер (например, Patch Set 2).


### Что сделать до начала работы

Зайти под своим логином `<USERNAME>` и паролем на сайт https://review.compscicenter.ru/login/. Пароль должен совпадать с тем, что используется на главном сайте CS центра. 
Если не получается войти, то сперва поменять пароль на compscicenter.ru (эта операция обновит пароль в системе ревью).
Если не помогло, то написать преподавателю, в крайнем случае на curators@compscicenter.ru

В настройках профиля https://review.compscicenter.ru/settings/ выбрать секцию SSH Keys, добавить публичный ключ.

TODO: добавить скриншот секции SSH Keys

Если вы не знаете как сгенерировать ключ, то читайте инструкции по ссылкам:

* https://help.github.com/articles/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent/
* https://gerrit-review.googlesource.com/Documentation/user-upload.html#configure_ssh_public_keys

Понимания, что такое приватный/публичный ключ не требуется, главное - уметь их использовать, но если хочется иметь общее представление, 
то начните [отсюда](https://ru.wikipedia.org/wiki/%D0%9A%D1%80%D0%B8%D0%BF%D1%82%D0%BE%D1%81%D0%B8%D1%81%D1%82%D0%B5%D0%BC%D0%B0_%D1%81_%D0%BE%D1%82%D0%BA%D1%80%D1%8B%D1%82%D1%8B%D0%BC_%D0%BA%D0%BB%D1%8E%D1%87%D0%BE%D0%BC).  


После добавления ssh-ключа, надо протестировать соединение командой:

```
$ ssh -v -p 29418 <USERNAME>@review.compscicenter.ru
```

Пример для почты `student@yandex.ru`:

```
ssh -v -p 29418 student.yandex.ru@review.compscicenter.ru
```

Обратите внимание на вывод команды. Если видите `Permission denied (publickey)`, то в первую очередь убедитесь, что добавили валидный публичный ключ в своём профиле и используете его при подключении.

Пример успешного соединения (обратите внимание на строку Welcome):

TODO: добавить скриншот вывода Welcome

### Репозиторий с задачами

TL;DR;

Клонируем git-репозиторий, создаём коммит с решением (сообщение коммита содержит Change-Id), пушим его по магической ссылке `refs/for/*`, где `*` - имя вашей личной ветки. 
Далее подробнее.

Перейдите в список проектов.

TODO: сделать скриншот


Если вы залогинены и список пустой - значит вам не выдали необходимые права. Сообщите об этом преподавателям, чтобы решить эту проблему.
Выберите в списке нужный проект. Если вы сдаёте задания через систему ревью первый раз, то скорее всего он будет только один.

На странице проекта вы увидите ссылку на клонирование репозитория. 
Обратите внимание, что надо использовать `SSH` а не `HTTP`, и надо воспользоваться командой, которая устанавливает commit-msg hook.

TODO: добавить скриншот команды. 

Например:

```bash
# Здесь клонируется проект spb/python_2018
git clone ssh://<USERNAME>@review.compscicenter.ru:29418/spb/python_2018 && scp -p -P 29418 <USERNAME>@review.compscicenter.ru:hooks/commit-msg python_2018/.git/hooks/
```

Если у вас возникли проблемы с установкой хука, то поставьте его руками, скачать сам hook можно по 
ссылке `http://review.compscicenter.ru/tools/hooks/commit-msg`, скопировать его надо в `.git/hooks`, не забудьте выдать права на исполнение файла.

Теперь, после установки хука, когда вы создаёте коммит и в сообщении отсутствует Change-Id, он будет сгенерирован автоматически. 
Подробнее об этом можно прочитать по ссылке: https://gerrit-documentation.storage.googleapis.com/Documentation/2.15.3/user-changeid.html

Перейдите в папку репозитория. Убедитесь, что у вас есть доступ к вашей личной ветке и master:

```
$ cd python_2018/
$ git remote show origin
...
  HEAD branch: master
  Remote branches:
    master         tracked   # ветка, где будут домашние задания
    ivanov.i.v     tracked   # ваша ветка, куда надо отправлять решения
...
```

Задания будут выкладываться в ветку `master`, а отправлять решения надо по магической ссылке `refs/for/ivanov.i.v` (`ivanov.i.v` - имя вашей личной ветки, сгенерированное на основе вашего ФИО)
Она действительно магическая, её нет в центральном репозитории, и магия не будет работать, 
если в сообщении коммита последним абзацем отсутствует строка `Change-Id: <SHA1>` (которую за вас любезно сгенерирует ранее установленный hook)

### Процедура сдачи домашнего задания (ver 1)

1. Обновите ветку master: `git checkout master && git pull`.
2. Убедитесь, что вы видите файлы в папке с номером задания: `hw00` для нулевой домашки, `hw01` для первой и т.д.
3. Создайте локальную ветку для домашнего задания: `git checkout -b homework00`.
4. Добавьте решение домашнего задания.
5. Закомитьте изменения:

```
# Добавляйте только необходимые файлы
git add ...
git add ...
git commit -m 'solved homework 00'
```

6. Убедитесь, что ваши изменения всегда размещены в рамках одного коммита. Веб-интерфейс позволяет смотреть изменения только в рамках одного коммита, а отправить на ревью 2 коммита с одинаковым Change-Id просто не получится, во время пуша вы получите ошибку 

```
same Change-Id in multiple changes.
Squash the commits with the same Change-Id or ensure Change-Ids are unique for each commit
``` 

Если коммит будет один, то это решит проблему того, что изменения размазаны по разным страницам.
 
Отправьте изменения на ревью командой `git push origin HEAD:refs/for/*`, где * - имя вашей личной ветки, например

```bash
git push origin HEAD:refs/for/ivanov.i.v
```

После этого в веб интерфейсе появится Change (аналог Pull Request на GitHub), там преподаватель будет оставлять свои комментарии.

7. Чтобы исправить задание, добавьте новые изменения командой `git commit --amend --no-edit`. Этой командой мы обновим hash коммита, но Change-Id не изменится. 
Так система ревью после отправки ваших правок поймёт, что есть новые изменения в рамках существующего `Change` и нужно создать новый Patch Set. 
Отправить правки на ревью нужно обычной командой `git push origin HEAD:refs/for/*`. 
Обратите внимание, что, несмотря на `--amend`, ключ `--force` при пуше не нужен. 


### Процедура сдачи домашнего задания (ver 2)

Перед тем, как создать новое ревью (в терминах gerrit его называют Change, аналог Pull Request на github.com или Merge Commit на gitlab.com), 
нужно разобраться, как система ревью определяет, что ваши коммиты принадлежат одному ревью. 
TL;DR; Для этого используется концепция Change-Id. 1 `Change-Id` == 1 ревью. 

Создадим наш первый коммит

```bash
# Создаём коммит с решением для задания 01
git add task1.cpp && git commit -m 'Solved homework 01'
```

Проверим лог

```
$ git log -1
commit 2da996e06a600b5bb2ea7bcf6143e8af658cb25d (HEAD -> master)
Author: I. V. Ivanov <author@example.com>
Date:   Wed Dec 4 11:32:00 2019 +0300

    Solved homework 01

    Change-Id: Ied45fa15b4a50c3a7c75594b7031518ccef7730b
```

Заметим, что hook, установленный ранее, в сообщение коммита добавил строку с Change-Id. 
Её можно было бы добавить и вручную, соблюдая формат, тогда hook оставил бы оригинальное сообщение без изменений.
Здесь `Ied45fa15b4a50c3a7c75594b7031518ccef7730b` - это id нашего будущего `Change`.   

Отправим решение на ревью

```bash
# Добавляем магический префикс refs/for/, так gerrit понимает, что мы хотим отправить изменения на ревью
git push origin HEAD:refs/for/ivanov.i.v
```

Cперва gerrit попытается найти существующее ревью (т.е. Change). Для этого он сравнит:

* Change-Id
* Имя репозитория
* Имя ветки (в примере выше это `ivanov.i.v`)

Если ревью не было найдено - gerrit создаст новый Change и добавит в него PatchSet1 (наши первые изменения на ревью)
Если ревью было найдено, gerrit добавит изменения как новый PatchSetN.

Внесём изменения в наш коммит


Полезные ссылки:
User Guide https://gerrit-documentation.storage.googleapis.com/Documentation/2.15.3/intro-user.html


## Для преподавателя

#### Руководство:

1. Попросить кураторов сгенерировать проект-репозиторий. Как только это будет сделано, по адресу https://review.compscicenter.ru/admin/repos можно будет найти созданный проект.
2. Ознакомиться с руководством студентов по отправке кода на ревью. Каждый студент работает со своей личной веткой и прогресса других студентов не видит.
3. Может возникнуть ситуация, когда студент записывается на курс после генерации проекта в системе ревью (у них есть такая возможность, если срок записи на курс ещё не закончен). 
В этом случае нужно прислать кураторам email студента, который желает получить доступ в систему ревью.

#### Подробнее о том, как происходит генерация проекта:

1. Создание проекта с именем `<PROJECT_NAME>`

    Имя проекта `<PROJECT_NAME>` генерируется по шаблону:

    ```
    (<city_code>/)<course_slug>_<course_year>
    # Для курса https://compscicenter.ru/courses/python/2018-autumn/
    spb/python_2018
    # Если курс заочный, то город не учитывается
    python_2018
    ```

2. Создание группы проверяющих с именем `<PROJECT_NAME>-reviewers`. В данную группу будут добавлены все преподаватели с ролью "проверяющий ДЗ" на основном сайте CS центра. Группа является владельцем проекта и имеет полный доступ к редактированию прав.

3. Создание группы студентов с именем `<PROJECT_NAME>-students`. После добавления студента в эту группу у него появляется возможность клонировать репозиторий.

4. Каждому студенту будут выданы права на создание ревью для своей личной ветки.

Если хочется разобраться в деталях, почему назначены те или иные права доступа, придётся прочитать [документацию](https://review.compscicenter.ru/Documentation/access-control.html).

Обзорно узнать о том, как работает система ревью gerrit, можно по [ссылке](https://review.compscicenter.ru/Documentation/intro-how-gerrit-works.html).
