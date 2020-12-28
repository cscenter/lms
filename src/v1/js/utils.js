import {get as getCookie} from 'es-cookie';
import template from 'lodash-es/template';

export function getLocalStorageKey(textarea) {
    return (window.location.pathname.replace(/\//g, "_")
    + "_" + textarea.name);
}

export function csrfSafeMethod(method) {
    // These HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

export function getCSRFToken() {
    return getCookie(window.__CSC__.config.csrfCookieName);
}

export function getTemplate (id) {
    return template(document.getElementById(id).innerHTML);
}

export function createNotification(msg, theme='default', position='bottom-right') {
    $.jGrowl(msg, { theme: theme, position: position });
}

export function showComponentError(error, msg='An error occurred while loading the component') {
    console.error(error);
    createNotification(msg, 'error');
}

// TODO: share with v2?
export function getSections() {
    if (document.body.hasAttribute("data-init-sections")) {
        let sections = document.body.getAttribute("data-init-sections");
        return sections.split(",");
    } else {
        return [];
    }
}
