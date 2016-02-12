(function ($) {
    "use strict";

    var gradebook_unsaved = 0;

    var gradebook = $("#gradebook");

    var scrollButtonsWrapper = $(".header", gradebook);

    var finalGradesWrapper = $("#grades");

    var totalWrapper = $("#total");

    var assignmentsWrapper = $("#assignments");

    var buttonSaveForm = $("button#marks-sheet-save");

    var buttonDownloadCSV = $(".marks-sheet-csv-link");

    var fn = {
        Launch: function () {
            fn.initFormSaveButton();
            fn.initFinalGradeSelect();
            fn.initAssignmentGradeInput();
            fn.initFinalGradeSelectBehavior();
            fn.scrollButtons();
            //fn.restrictGradeInputChars();
            //fn.gradeInputFocus();
            // TODO: Sticky headers
            // TODO: arrow up and down inc/dec - keypress event for better performance. Inspire by jquery-arrow
            // TODO: quick select for

        },

        initFormSaveButton: function() {
            // Lock save button until nothing changed.
            buttonSaveForm.attr("disabled", "disabled");
        },

        initFinalGradeSelect: function() {
            finalGradesWrapper.find("select").each(function() {
                $(this).data("value", $(this).val());
            });
        },

        initAssignmentGradeInput: function() {
            assignmentsWrapper.on("blur", "input", function (e) {
                var $this = $(this),
                    $target = $(e.target);
                // Validate min-max
                if ($this.val() < 0) {
                    $this.val(0);
                }
                var maxGrade = $this.closest(".assignment").data("max");
                if ($this.val() > maxGrade) {
                    $this.val(maxGrade);
                }
                // Is it integer value?
                if ($this.val() != parseInt($this.val(), 10)) {
                    $this.val("");
                }

                fn.toggleSaveButton($target);
            });
        },

        initFinalGradeSelectBehavior: function() {
            gradebook.on("change", "select", function (e) {
                var $target = $(e.target);
                fn.toggleSaveButton($target);
            });
        },

        toggleSaveButton: function(element) {
            var current_value = element.val();
            var saved_value = element.data("value");
            var gradeWrapper;
            if (current_value != saved_value) {
                if ( element[0].nodeName.toLowerCase() === 'input' ) {
                    gradeWrapper = element;
                } else if (element[0].nodeName.toLowerCase() === 'select') {
                    gradeWrapper = element.parent();
                }
                gradeWrapper.addClass("__unsaved");
                gradebook_unsaved++;
                if (gradebook_unsaved > 0) {
                    buttonSaveForm.removeAttr("disabled");
                    buttonDownloadCSV.addClass("disabled");
                }
            } else {
                if ( element[0].nodeName.toLowerCase() === 'input' ) {
                    gradeWrapper = element;
                } else if (element[0].nodeName.toLowerCase() === 'select') {
                    gradeWrapper = element.parent();
                }
                gradeWrapper.removeClass("__unsaved");
                gradebook_unsaved--;
                if (gradebook_unsaved == 0) {
                    buttonSaveForm.attr("disabled", "disabled");
                    buttonDownloadCSV.removeClass("disabled");
                }
            }
        },

        // TODO: Refactor
        scrollButtons: function() {
            scrollButtonsWrapper.on("click", ".scroll.left", function() {
                fn.scroll(-1, 0);
            });
            scrollButtonsWrapper.on("click", ".scroll.right", function() {
                fn.scroll(1, 0);
            });
            if (assignmentsWrapper.find('.assignment').length > 6) {
                scrollButtonsWrapper.css("visibility", "visible");
                totalWrapper.css("box-shadow", "5px 0 5px -5px rgba(0, 0, 0, 0.4)");
            }
        },

        scroll: function (xdir, ydir) {
            var assignmentColumnWidth = 100,
                rowHeight = 20,
                xinc = assignmentColumnWidth * parseInt(xdir),
                yinc = rowHeight * 5 * parseInt(ydir);
            if (xinc != 0) {
                var scrollXOffset = assignmentsWrapper.scrollLeft();
                assignmentsWrapper.scrollLeft(scrollXOffset + xinc);
            }
            if (yinc != 0) {
                var scrollYOffset = assignmentsWrapper.scrollTop();
                assignmentsWrapper.scrollTop(scrollYOffset + yinc);
            }
        },
        // Disabled
        gradeInputFocus: function() {
            assignmentsWrapper.on("click", ".assignment input", function() {
                $(this).select();
            });
        },

        restrictGradeInputChars: function() {
        }
    };

    $(document).ready(function () {
        fn.Launch();
    });

})(jQuery);




    $('.marks-table.teacher').on('focus', 'input,select', function (e) {
        $(this).closest("tr").addClass("active");
        var tdIdx = $(this).closest("td").index();
        ($(this).closest(".marks-table")
         .find("tr > td.content:nth-child(" + (tdIdx + 1) +")")
         .addClass("active"));
    });

    $('.marks-table.teacher').on('blur', 'input,select', function (e) {
        $(this).closest(".marks-table").find("td,tr").removeClass("active");
    });

    $('.marks-table.staff').on('click', 'td.content', function (e) {
        $(this).closest(".marks-table").addClass("focused");
        $(this).closest(".marks-table").find("td,tr").removeClass("active");
        $(this).closest("tr").addClass("active");
        var tdIdx = $(this).closest("td").index();
        ($(this).closest(".marks-table")
         .find("tr > td.content:nth-child(" + (tdIdx + 1) +")")
         .addClass("active"));
    });