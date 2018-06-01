import './student_search';
import './diplomas_tex';
import unreadNotifications from './course_offering';

import React from 'react';
import ReactDOM from 'react-dom';

import Facebook from 'components/Facebook';


const COMPONENTS = {
    Facebook
};


function renderComponentInElement(el) {
    let Component = COMPONENTS[el.id];
    if (!Component) return;

    const props = Object.assign({}, el.dataset);
    // get props from elements data attribute
    Object.keys(props).map((k) => {
        if (k === "init") {
            props[k] = JSON.parse(props[k]);
        }
    });

    ReactDOM.render(<Component {...props} />, el);
}


$(document).ready(function () {
    unreadNotifications();
    document
        .querySelectorAll('.__react-root')
        .forEach(renderComponentInElement);
});

