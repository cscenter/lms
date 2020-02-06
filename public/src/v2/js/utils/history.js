import _isEqual from 'lodash-es/isEqual';

// TODO: create typescript interface for `getFilterState` return value (see `FilterState`)

export function getHistoryState(location, initialState) {
    if (!location.state) {
        return this.getFilterState(initialState);
    } else {
        return this.getFilterState(location.state);
    }
}


/**
 * Update React component state with filter state stored in a history entry.
 * @param location Implements a subset of the `window.location` interface. See https://github.com/ReactTraining/history/blob/master/docs/GettingStarted.md#listening
 * @param action One of PUSH, REPLACE, or POP
 */
export function onPopState(location, action) {
    if (action !== "POP") {
        return;
    }
    const newState = getHistoryState.call(this, location, this.props.initialState);
    console.debug(`History.listen: new state`, JSON.stringify(newState));
    this.setState(newState);
}

/**
 * Push filter state to the browser's session history stack.
 * @param history Object returned by `createBrowserHistory`
 */
export function historyPush(history) {
    const currentState = this.getFilterState(this.state);
    const historyState = getHistoryState.call(this, history.location, this.props.initialState);
    console.debug('History.push: current state', JSON.stringify(currentState));
    console.debug('History.push: history state', JSON.stringify(historyState));
    if (!_isEqual(currentState, historyState)) {
        console.debug("push new history state");
        let searchString = currentState.toURLSearchParams().toString();
        searchString = _updateSearchString(searchString);
        history.push({
            pathname: history.location.pathname,
            search: '?' + searchString,
            state: currentState
        });
    }
}


function _updateSearchString(URLSearchString) {
    // Note, that `,` is a reserved character and is not equivalent
    // to their percent-encoded variants, but neither the URI standard
    // nor the HTTP(S) URI scheme specs define a special role
    // for `,` in the query component. This means we may use `,`
    // for whatever we want and consider a `,` equivalent to `%2C` :>
    return URLSearchString.replace('%2C', ',');
}