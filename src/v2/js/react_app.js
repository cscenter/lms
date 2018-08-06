import React from 'react';
import ReactDOM from 'react-dom';

import {showComponentError} from 'utils';

export function renderComponentInElement(el) {
    let componentName = el.id;
    import(/* webpackChunkName: "[request]" */ `apps/${componentName}`)
        .then(component => {
            let props = {
                initialState: {}
            };
            let init = el.getAttribute('data-init');
            if (init !== null) {
                let data = JSON.parse(init);
                if (data.props !== undefined) {
                    Object.keys(data.props).map((k) => {
                        props[k] = data.props[k];
                    });
                    delete data.props;
                }
                props.initialState = data.state || {};
            }
            let Component = component.default;
            ReactDOM.render(React.createElement(Component, props), el);
        })
        .catch(error => showComponentError(error));
}