let template = require('lodash.template');

export function getLocalStorageKey(textarea) {
    return (window.location.pathname.replace(/\//g, "_")
    + "_" + textarea.name);
}

export function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

export function getTemplate (id) {
    return template(document.getElementById(id).innerHTML);
}
