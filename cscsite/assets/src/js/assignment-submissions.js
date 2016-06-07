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
            assignmentSelect.multiselect({
                maxHeight: 500,
                includeSelectAllOption: true,
                selectAllText: 'Выбрать все',
                onChange: function(option, checked) {
                    if (checked) {
                        assignmentsSelectedCount++;
                        $(option).data('assignments', assignmentsSelectedCount);
                    }
                    else {
                        $(option).data('assignments', '');
                    }
                },
                buttonText: function(options) {
                    return options.length + ' выбрано';
                },
                onInitialized: function(select, container) {
                    $(container).closest('.filters').find('.loading').remove();
                }
            });

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