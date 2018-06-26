import $ from 'jquery';
import Noty from 'noty';

export const MOBILE_VIEWPORT_MAX = 992;

export function getSections() {
    if (document.body.hasAttribute("data-init-sections")) {
        let sections = document.body.getAttribute("data-init-sections");
        return sections.split(",");
    } else {
        return [];
    }
}

export function showComponentError(error, msg='An error occurred while loading the component') {
    console.error(error);
    alert(error);  // TODO: add jGrowl or something similar
}

export function showNotification(msg, options) {
    new Noty({
        layout: 'topLeft',
        type: 'info',
        theme: 'bootstrap-v4',
        text: msg,
        timeout: 2000,
        ...options
    }).show();
}

export function showErrorNotification(msg) {
    showNotification(msg, {type:"error", timeout: false});
}

export function showBodyPreloader() {
    $(document.body).addClass("_fullscreen").addClass("_loading");
}

export function hideBodyPreloader() {
    $(document.body).removeClass("_fullscreen").removeClass("_loading");
}