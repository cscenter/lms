(function ($) {
    "use strict";

    var review_form = $("#review-form form");

    var fn = {
        launch: function () {
            fn.reviewFormValidation();
        },

        reviewFormValidation: function() {
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
                        $.jGrowl('Выставьте все оценки для завершения проверки.',
                        { position: 'bottom-right', theme: 'error' });
                        $("input[type=submit]", review_form).removeAttr("clicked");
                    }
                }
            });

            review_form.find("input[type=submit]").click(function() {
                $("input[type=submit]", $(this).parents("form")).removeAttr("clicked");
                $(this).attr("clicked", "true");
            });
        },
    };

    $(document).ready(function () {
        fn.launch();
    });

})(jQuery);