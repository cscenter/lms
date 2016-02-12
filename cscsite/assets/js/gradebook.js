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
            fn.initFinalGradeSelectBehavior();
            fn.initAssignmentGradeInput();
            fn.assignmentGradeInputIncrementByArrows();
            fn.scrollButtons();
            //fn.restrictGradeInputChars();
            //fn.gradeInputFocus();
            // TODO: Maby should replace with 1 .on delegate event
            // TODO: Sticky headers
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
            assignmentsWrapper.on("change", "input", function (e) {
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

        assignmentGradeInputIncrementByArrows: function() {
            assignmentsWrapper.on("keydown", ".assignment input", function(e) {
                if (e.keyCode === 38 || e.keyCode == 40) {
                    var that = this; // input object
                    // Mb it's incredibly stupid practice, who cares?
                    if (that.increment === undefined || that.decrement === undefined) {
                        that.increment = $.arrowIncrement.prototype.increment;
                        that.decrement = $.arrowIncrement.prototype.decrement;
                    }
                    // TODO: get min/max

                    that.opts = {
                        // Slightly modified version of original $.arrowIncrement method
                        parseFn: function (value) {
                            var parsed = value.match(/^(\D*?)(\d*(,\d{3})*(\.\d+)?)\D*$/);
                            if (parsed && parsed[2]) {
                                if (parsed[1] && parsed[1].indexOf('-') >= 0) {
                                    return -parsed[2].replace(',', '');
                                } else {
                                    return +parsed[2].replace(',', '');
                                }
                            }
                            // Empty string as 0
                            if (value.length == 0) {
                                return 0;
                            }
                            return NaN;
                        }
                    };
                    that.$element = $(this);
                    if (e.keyCode === 38) { // up
                        that.increment();
                    } else if (e.keyCode === 40) { // down
                        that.decrement();
                    }
                }
            });
        },

        restrictGradeInputChars: function() {
        }
    };

    $(document).ready(function () {
        fn.Launch();
    });

})(jQuery);