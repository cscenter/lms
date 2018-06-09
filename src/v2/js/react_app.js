import React from 'react';
import ReactDOM from 'react-dom';

import {showComponentError} from 'utils';

export function renderComponentInElement(el) {
    let componentName = el.id;
    import(/* webpackChunkName: "[request]" */ `sections/${componentName}`)
        .then(component => {
            const props = Object.assign({}, el.dataset);
            // get props from elements data attribute
            Object.keys(props).map((k) => {
                if (k === "init") {
                    props[k] = JSON.parse(props[k]);
                }
            });
            let Component = component.default;
            ReactDOM.render(React.createElement(Component, props), el);
        })
        .catch(error => showComponentError(error));
}