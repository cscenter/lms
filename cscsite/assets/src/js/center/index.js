import {reviewFormValidation} from './projects_report';

import styles from 'sass/center/style.scss';

// Let's leave it here for now
$(function() {
    if (document.getElementById('questions-wrapper') !== null) {
        let faqWrapper = $('#questions-wrapper');
        faqWrapper.on('click', '.panel-title', function(e) {
            // Replace js animation with css.
            e.preventDefault();
            const open = $(this).attr("aria-expanded") === "true";
            $(this).parent().next().toggleClass('collapse').attr("aria-expanded", !open);
            $(this).attr("aria-expanded", !open);
        });
    }

    // Leave it here for now
    reviewFormValidation();
});

