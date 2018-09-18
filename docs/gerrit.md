### Delete Project in Gerrit

```bash
# delete .git folder inside gerrit app folder /data/gerrit/git/
ssh -p 29418 admin@review.compscicenter.ru gerrit flush-caches --cache projects
# TODO: run gc?

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


## Для студента

Чтобы успешно отправлять решения в систему code review, нужно знать, как работать с ssh клиентом на вашей платформе и уметь пользоваться git.

### Обозначения:

`<USERNAME>` - логин на сайте review.compscicenter.ru. Возьмите ваш email на сайте compscicenter.ru и замените `@` на `.`, получите логин в системе ревью.

`Change` - изменения, которые вы отправляете на ревью. Можно провести аналогию с Pull Request на github.com

`Patch Set` - изменения в рамках `Change`. Когда вас просят доработать код, ваши отправленные изменения будут называться `Patch Set`.

`Change-Id` - SHA1, который вы добавляете последним абзацем в сообщение коммита (`Change-Id: <SHA1>`). По нему система ревью сможет связывать ваш `Patch Set` с `Change`.


### Что сделать до начала работы

Зайти под своим логином `<USERNAME>` и паролем на сайт. Пароль должен совпадать с тем, что используется на сайте compscicenter.ru. 
Если не получается войти, то сперва поменять пароль на сайте compscicenter.ru (эта операция обновит пароль в системе ревью)
и если не помогает, то написать кураторам.

В настройках профиля https://review.compscicenter.ru/settings/ выбрать секцию SSH Keys, добавить публичный ключ.
Подробнее как сгенерировать ключ и добавить себе в профиль читайте по ссылке (en) https://gerrit-review.googlesource.com/Documentation/user-upload.html#ssh


Протестировать соединение можно командой:

```
$ ssh -v -p 29418 <USERNAME>@review.compscicenter.ru
```

Пример для почты `student@yandex.ru`:

```
ssh -v -p 29418 student.yandex.ru@review.compscicenter.ru
```

Обратите внимание на вывод команды. Если видите `Permission denied (publickey)`, то в первую очередь убедитесь, что добавили валидный публичный ключ в своём профиле и используете его при подключении.


#### Как сдавать задание на code review:

TL;DR;

Клонируем git-репозиторий, создаём коммит с решением (сообщение коммита содержит Change-Id), пушим его по магической ссылке `refs/for/*`, где `*` - имя вашей личной ветки. 
Далее подробнее.


Склонируйте репозиторий

```
git clone ssh://<USERNAME>@review.compscicenter.ru:29418/<PROJECT_NAME>.git
```

имя проекта `<PROJECT_NAME>` генерируется по шаблону: 

```
<city_code>/<course_slug>_<course_year>
# Для курса https://compscicenter.ru/courses/python/2018-autumn/
spb/python_2018
```

Пример:

```
git clone ssh://student.yandex.ru@review.compscicenter.ru:29418/spb/python_2018.git
```


Посмотрите, к каким remote веткам у вас есть доступ:

```
cd spb/python_2018
$ git remote show origin
...
  HEAD branch: master
  Remote branches:
    master         tracked
    ivanov.i.v     tracked
...
```

Задания будут выкладываться в ветку `master`, а отправлять решения надо по магической ссылке `refs/for/ivanov.i.v` (`ivanov.i.v` - имя вашей личной ветки, сгенерированное на основе вашего ФИО)
Она действительно магическая, её нет в центральном репозитории, и магия не будет работать, если в сообщении коммита последним абзацем отсутствует строка `Change-Id: <SHA1>`.

Вы можете самостоятельно сгенерировать SHA1 на основе ваших изменений, но можно немного упростить себе жизнь и установить git hook

```
# Из рабочей папки
curl -Lo .git/hooks/commit-msg http://review.compscicenter.ru/tools/hooks/commit-msg
# или
scp -p -P 29418 <USERNAME>@review.compscicenter.ru:hooks/commit-msg .git/hooks/
# Убедитесь, что есть права на его исполнение
chmod u+x .git/hooks/commit-msg
```

Теперь, когда вы создаёте коммит и в сообщении отсутствует Change-Id, он будет сгенерирован автоматически. 
Подробнее о Change-Id и зачем он нужен можно ознакомиться здесь https://gerrit-documentation.storage.googleapis.com/Documentation/2.15.3/user-changeid.html

Как только вы успешно отправите свои изменения на ревью командой `git push origin HEAD:refs/for/*`, где `*` - имя вашей личной ветки, 
в веб интерфейсе появится Change, там преподаватель будет оставлять свои комментарии.

В процессе проверки вашего кода, у вас могут попросить внести изменения (в системе ревью такие изменения называются PatchSet). Чтобы добавить их к текущему Change, отправьте коммит с тем же Change-Id.

Полезные ссылки:
User Guide https://gerrit-documentation.storage.googleapis.com/Documentation/2.15.3/intro-user.html


## Для преподавателя

Перед публикацией первого задания на ревью, нужно обратиться к кураторам, чтобы они создали проект в системе ревью и сгенерировали студентам необходимые права доступа.

Имя проекта `<PROJECT_NAME>` генерируется по шаблону:

```
<city_code>/<course_slug>_<course_year>
# Для курса https://compscicenter.ru/courses/python/2018-autumn/
spb/python_2018
```

Все права в системе ревью выдаются на основе групп. Для каждого проекта дополнительно создаётся 2 группы:

`<PROJECT_NAME>`-reviewers  Имеют полный доступ к редактированию прав доступа.
`<PROJECT_NAME>`-students.  Даёт доступ к чтению ветки master. Туда необходимо добавлять группы студентов.

В группу владельцев проекта будут добавлены преподаватели, которые имеют роль "проверяющий ДЗ" на сайте центра. Владелец проекта имеет полный доступ к редактированию прав.
Может возникнуть ситуация, когда студент записывается на курс после создания проекта в системе ревью (у них есть такая возможность, если срок записи на курс ещё не закончен).
Вы можете вручную добавить ему необходимые права (по аналогии с теми, что уже будут добавлены), главное не забудьте добавить его в группу `<PROJECT_NAME>`-students, иначе он не сможет склонировать репозиторий.

Права нужно выдавать на 2 ссылки (на примере malysh.k.i):

* `refs/heads/malysh.k.i`
* `refs/for/refs/heads/malysh.k.i`

После создания проекта он появится на странице https://review.compscicenter.ru/admin/projects. В его описании будут ссылки на клонирование репозитория. 
Это можно сделать 2мя способами:

* https (username - тот, что используется на сайте, пароль - надо сгенерировать в настройках профиля (раздел HTTP Credentials)
* ssh (в настройках профиля надо добавить публичный ключ, раздел SSH Keys)  

Права доступа успешно можно редактировать только в старом интерфейсе (в футере справа есть Switch to Old UI)
Подробно о системе прав в документации https://gerrit-review.googlesource.com/Documentation/access-control.html



TODO: 1 коммит на домашку, иначе diff размазывается и проверять сложно