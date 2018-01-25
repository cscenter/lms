import i18n from "./i18n";

import template from 'lodash-es/template';

export const GROUPS = {
    1: i18n.groups.STUDENT_CENTER,
    4: i18n.groups.VOLUNTEER,
    3: i18n.groups.GRADUATE_CENTER
};

export const COLOR_PALETTE = [
    '#5cb85c',
    '#f96868',
    '#F6BE80',
    '#515492',
    '#4F86A0'
];

export const URLS = window.URLS;

export function getTemplate (id) {
    return template(document.getElementById(id).innerHTML);
}
