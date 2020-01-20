### Памятка по history API в react-js

Для примера будем считать, что в URL помещаются query-параметры из фильтра.

```js
import { createBrowserHistory } from "history";
const history = createBrowserHistory();
```

В `componentDidMount` регистрируем обработчик, который будет следить за изменением истории браузера:

```js
// componentDidMount
this.unlistenHistory = history.listen((location, action) => {
    ...
    this.setState({...});
});
```

В `componentWillUnMount` не забывает удалять обработчик:

```js
// componentWillUnMount
this.unlistenHistory();
```

После изменения состояния одного из фильтров мы должны добавить запись в историю браузера. Делаем это с помощью метода `history.push`, который вызываем как callback для метода `setState` компонента.

```js
// Если текущее состояние фильтров на вершине стека истории браузера != текущему состоянию фильтров компонента, то обновим историю
if (!_isEqual(currentState, historyState)) {
    history.push({
        pathname: history.location.pathname,
        search: `?foo=42&bar=42`, // query-строка со значениями всех фильтров, которые храним в истории браузера
        state: filterState  // состояние всех фильтров, которое можно добавить через вызов `setState`
    });
}
```

В методе `componentDidUpdate` это сделать легко не получится, потому что когда меняется состояние фильтра, мы должны знать, сделал это обработчик `history.listen` или пользователь.
Если это сделал обработчик, то историю добавлять не нужно во избежание дубликатов. Чтобы отличать источники события, придётся заводить доп. переменную в состоянии.