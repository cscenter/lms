import {queryAll} from "@drivy/dom-query";

export function launch() {
    queryAll('.collapsible').onDelegate('.card__header', 'click', function (event) {
        event.preventDefault();
        const isOpened = this.getAttribute("aria-expanded") === "true";
        let answerElement = this.nextElementSibling;
        answerElement.classList.toggle('collapse');
        answerElement.setAttribute('aria-expanded', !isOpened);
        this.setAttribute('aria-expanded', !isOpened);
    });
}
