(function ($) {
    "use strict";

    var faq = $("#questions");

    var fn = {
        launch: function () {
            fn.toggleUniversity();
            fn.toggleHasJob();
        },

        toggleUniversity: function() {
            $('select[name$="-university"]').change(function () {
                var disabled = parseInt(this.value) !== 10;
                $('input[name$="-university_other"]').prop('disabled', disabled);

            });
        },

        toggleHasJob: function() {
            $('select[name$="-has_job"]').change(function () {
                var disabled = this.value !== 'Да';
                $('input[name$="-workplace"]').prop('disabled', disabled);
                $('input[name$="position"]').prop('disabled', disabled);

            });
        },
    };

    $(document).ready(function () {
        fn.launch();
    });

})(jQuery);