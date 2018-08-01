import React from 'react';
import ReactDOM from 'react-dom';

import {showComponentError} from 'utils';

export function renderComponentInElement(el) {
    let componentName = el.id;
    import(/* webpackChunkName: "[request]" */ `apps/${componentName}`)
        .then(component => {
            const props = Object.assign({}, el.dataset);
            // get props from elements data attribute
            Object.keys(props).map((k) => {
                if (k === "init") {
                    // Allow passing initial props from backend
                    let data = JSON.parse(props[k]);
                    if (data.props !== undefined) {
                        Object.keys(data.props).map((k) => {
                            props[k] = data.props[k];
                        });
                        delete data.props;
                    }
                    props[k] = data;
                }
            });
            let Component = component.default;
            ReactDOM.render(React.createElement(Component, props), el);
        })
        .catch(error => showComponentError(error));
}