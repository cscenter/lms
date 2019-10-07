import $ from 'jquery';

export function launch() {
    $('.collapsible').on('click', '.card__header', function(e) {
        // Replace js animation with css.
        e.preventDefault();
        const open = this.getAttribute("aria-expanded") === "true";
        $(this).next().toggleClass('collapse').attr("aria-expanded", !open);
        this.setAttribute("aria-expanded", !open);
    });
}
