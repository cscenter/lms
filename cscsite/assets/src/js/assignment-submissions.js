(function ($) {
    "use strict";

    var assignmentsSelectedCount = 0;

    var filtersForm = $(".filters form");

    var assignmentSelect = $("#assignments-select");

    var assignmentsInput = filtersForm.find('input[name=assignments]');

    var assignmentSelectButton = $("#assignments-select-button");


    var fn = {
        Launch: function () {
            fn.initFiltersForm();
        },

        initFiltersForm: function() {
            assignmentSelect.selectpicker({
                maxOptions: 2,
                iconBase: 'fa',
                tickIcon: 'fa-check'
            });
            assignmentSelect.on('loaded.bs.select', function (e) {
              $(this).closest('.filters').find('.loading').remove();
            });

            // TODO: simplify
            filtersForm.on('submit', function () {
                var selected = $.map(assignmentSelect.find('option:selected'), function (el, i) {
                    return $(el).val();
                });
                var selectedAssignments = selected.join(",");
                assignmentsInput.val(selectedAssignments);
                window.location = filtersForm.attr("action") + selectedAssignments;
                return false;
            })
        },
    };

    $(document).ready(function () {
        fn.Launch();
    });

})(jQuery);