import $ from 'jquery';
import 'bootstrap/js/src/tab';

export function launch() {
    $('.nav-tabs a').on('click', function(e) {
        // Replace js animation with css.
        e.preventDefault();
        $(this).tab('show');
    });
}