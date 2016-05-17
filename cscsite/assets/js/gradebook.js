(function ($) {
    "use strict";

    var gradebook = $("#gradebook");

    var buttonDownloadCSV = $(".marks-sheet-csv-link");

    var scrollButtonsWrapper = $(".header", gradebook);

    var finalGradesWrapper = $("#grades");

    var totalWrapper = $("#total");

    var assignmentsWrapper = $("#assignments");

    var fn = {
        Launch: function () {
            fn.downloadCSVButton();
            fn.finalGradeSelect();
            fn.assignmentGradeInputValidator();
            fn.assignmentGradeInputIncrementByArrows();
            fn.scrollButtons();
            fn.fileInput();
        },

        downloadCSVButton: function() {
            buttonDownloadCSV.click(function() {
                if (gradebook.find(".__unsaved").length > 0) {
                    swal({
                        title: "",
                        text: "Сперва сохраните форму,\n" +
                              "чтобы скачать актуальные данные.",
                        type: "warning",
                        confirmButtonText: "Хорошо"
                    });
                    return false;
                }
            });
        },

        finalGradeSelect: function() {
            // Store initial value
            finalGradesWrapper.find("select").each(function() {
                $(this).data("value",
                             $(this).find('option').filter(function () {
                                return $(this).prop('defaultSelected');
                             }).val());
            });
            gradebook.on("change", "select", function (e) {
                var $target = $(e.target);
                fn.toggleState($target);
            });
        },

        assignmentGradeInputValidator: function() {
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

                fn.toggleState($target);
            });
        },

        toggleState: function(element) {
            var current_value = element.val();
            var saved_value = element.data("value");
            var gradeWrapper;
            if ( element[0].nodeName.toLowerCase() === 'input' ) {
                gradeWrapper = element;
            } else if (element[0].nodeName.toLowerCase() === 'select') {
                gradeWrapper = element.parent();
            }
            if (current_value != saved_value) {
                gradeWrapper.addClass("__unsaved");
            } else {
                gradeWrapper.removeClass("__unsaved");
            }
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

        // TODO: Refactor
        scrollButtons: function() {
            scrollButtonsWrapper.on("click", ".scroll.left", function() {
                fn.scroll(-1, 0);
            });
            scrollButtonsWrapper.on("click", ".scroll.right", function() {
                fn.scroll(1, 0);
            });

            totalWrapper.css("box-shadow", "5px 0 5px -5px rgba(0, 0, 0, 0.4)");

            if (assignmentsWrapper.width() <= assignmentsWrapper.find('.scrollable').width()) {
                scrollButtonsWrapper.css("visibility", "visible");
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

        fileInput: function () {
            $("#input-id").fileinput({
                'showUpload': false,
                'language': 'ru',
                'previewFileType': 'text',
                'allowedFileTypes': ['text'],
                'allowedFileExtensions': ['txt', 'csv'],
                'showPreview': false,
                'showRemove': false,
                'maxFileCount': 1,
                browseIcon: '<i class="fa fa-folder-open"></i> &nbsp;',
                removeIcon: '<i class="fa fa-trash"></i> ',
                uploadIcon: '<i class="fa fa-upload"></i> ',
                cancelIcon: '<i class="fa fa-times-circle-o"></i> ',
                msgValidationErrorIcon: '<i class="fa fa-exclamation-circle"></i> '
            });
        },

        restrictGradeInputChars: function() {
        }
    };

    $(document).ready(function () {
        fn.Launch();
    });

})(jQuery);