(function ($) {
    "use strict";

    var faq = $("#questions");

    var fn = {
        launch: function () {
            fn.toggleUniversity();
            fn.toggleHasJob();
            fn.toggleStudyProjects();
            fn.toggleWhereDidYouLearn();
        },

        toggleUniversity: function() {
            $('select[name$="-university"]').change(function () {
                var universityID = parseInt(this.value);
                var disabled = (universityID !== 10 && universityID !== 14);
                if (disabled) {
                    $('#university-other-row').addClass('hidden');
                } else {
                    $('#university-other-row')
                        .removeClass('hidden')
                        .find('input').focus();
                }
            });
        },

        toggleHasJob: function() {
            $('select[name$="-has_job"]').change(function () {
                var disabled = this.value !== 'yes';
                $('input[name$="-workplace"]').prop('disabled', disabled);
                $('input[name$="position"]').prop('disabled', disabled);

            });
        },

        toggleStudyProjects: function () {
            $('input[name$="-preferred_study_programs"]').change(function () {
                var code = this.value;
                var $textarea = $('textarea[name$=-preferred_study_programs_' + code + '_note]');
                if ($(this).is(':checked')) {
                    $textarea.closest('.col-xs-12').removeClass('hidden');
                } else {
                    $textarea.closest('.col-xs-12').addClass('hidden');
                }
            })
        },

        toggleWhereDidYouLearn: function () {
            $('input[name$="-where_did_you_learn"]').change(function () {
                if (this.value != 'other') {
                    return;
                }
                var $textarea = $('input[name$=-where_did_you_learn_other]');
                if ($(this).is(':checked')) {
                    $textarea.closest('.col-xs-12').removeClass('hidden');
                } else {
                    $textarea.closest('.col-xs-12').addClass('hidden');
                }
            })
        }
    };

    $(document).ready(function () {
        fn.launch();
    });

})(jQuery);