import {createNotification} from "../utils";

let review_form = $("#review-form form");

export function reviewFormValidation() {
    review_form.submit(function(event) {
        var clickedSubmitButton = $("input[type=submit][clicked=true]", review_form);
        if (clickedSubmitButton.attr('name') == 'review_form-send') {
            // Validate select's
            var all_has_value = true;
            $('select', review_form).each(function() {
               if ($(this).val() == "") {
                   all_has_value = false;
               }
            });
            if (!all_has_value) {
                event.preventDefault();
                const msg = 'Выставьте все оценки для завершения проверки.';
                createNotification(msg, 'error');
                $("input[type=submit]", review_form).removeAttr("clicked");
            }
        }
    });

    review_form.find("input[type=submit]").click(function() {
        $("input[type=submit]", $(this).parents("form")).removeAttr("clicked");
        $(this).attr("clicked", "true");
    });
}