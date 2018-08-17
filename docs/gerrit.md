### Delete Project in Gerrit

```bash
# delete .git folder inside gerrit app folder /data/gerrit/git/
ssh -p 29418 admin@review.compscicenter.ru gerrit flush-caches --cache projects
# TODO: run gc?

```

Чтобы успешно отправлять решения в систему code review, нужно знать, как работает ssh клиент на вашей платформе и уметь пользоваться git.


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


Обозначения:

`<USERNAME>` - ваш email на сайте compscicenter.ru, где символ `@` заменён на `.`.


Протестировать соединение можно командой:

```
$ ssh -v -p 29418 <USERNAME>@review.compscicenter.ru
```

Пример для почты `student@yandex.ru`:

```
ssh -v -p 29418 student.yandex.ru@review.compscicenter.ru
```

Если видите `Permission denied (publickey)`, то в первую очередь убедитесь, что добавили валидный публичный ключ в своём профиле и используете его при подключении.

Подробнее как сгенерировать ключ и добавить себе в профиль https://gerrit-review.googlesource.com/Documentation/user-upload.html#ssh
