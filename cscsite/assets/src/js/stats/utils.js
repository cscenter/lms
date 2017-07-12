import i18n from "./i18n";

let template = require('lodash.template');

export const GROUPS = {
    1: i18n.groups.STUDENT_CENTER,
    4: i18n.groups.VOLUNTEER,
    3: i18n.groups.GRADUATE_CENTER
};

export const URLS = window.URLS;

export function getTemplate (id) {
    return template(document.getElementById(id).innerHTML);
}
