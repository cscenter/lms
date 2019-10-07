import {showComponentError} from 'utils';
import {reviewFormValidation} from './projects_report';

// Let's leave it here for now
$(function() {
    if (document.getElementsByClassName('panel-group').length > 0) {
        $('.panel-group').on('click', '.panel-heading', function(e) {
            // Replace js animation with css.
            e.preventDefault();
            const open = $(this).attr("aria-expanded") === "true";
            $(this).next().toggleClass('collapse').attr("aria-expanded", !open);
            $(this).attr("aria-expanded", !open);
        });
    }

    // Leave it here for now
    reviewFormValidation();
});

