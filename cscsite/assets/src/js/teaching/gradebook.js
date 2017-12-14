import "vendor/jquery.arrow-increment.min"
import SweetAlert from "bootstrap-sweetalert";

const buttonDownloadCSV = $(".marks-sheet-csv-link");

let gradebookContainer = $("#gradebook-container");

let gradebook = $("#gradebook");

let scrollButtonsWrapper = $(".gradebook__controls");

const fn = {
    launch: function () {
        fn.finalGradeSelects();
        fn.restoreStates();
        fn.downloadCSVButton();
        fn.assignmentGradeInputValidator();
        fn.assignmentGradeInputIncrementByArrows();
        fn.scrollButtons();
    },

    /**
     * If browser supports html5 `autocomplete` attribute,
     * we can accidentally hide unsaved state on page reload.
     * Make sure set `defaultValue` for selects before calling this method.
     */
    restoreStates: function() {
        let inputs = document.querySelectorAll('#gradebook .__input');
        Array.prototype.forEach.call(inputs, fn.toggleState);
        let selects = document.querySelectorAll('#gradebook select');
        Array.prototype.forEach.call(selects, fn.toggleState);
    },

    downloadCSVButton: function() {
        buttonDownloadCSV.click(function() {
            if (gradebook.find(".__unsaved").length > 0) {
                SweetAlert({
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

    /**
     * Store `defaultSelected` in <select> DOM object for consistency with inputs.
     */
    finalGradeSelects: function() {
        gradebook.find("select").each(function() {
            this.defaultValue = $(this).find('option').filter(function () {
                return $(this).prop("defaultSelected");
            }).val();
        });
        gradebook.on("change", "select", function (e) {
            fn.toggleState(e.target);
        });
    },

    assignmentGradeInputValidator: function() {
        gradebook.on("keypress", "input.__assignment", fn.validateNumber);
        // FIXME: instead of implicitly fix user input - highlight this error
        gradebook.on("change", "input.__assignment", function (e) {
            const value = parseInt(this.value, 10);
            if (!$.isNumeric(this.value) || !Number.isInteger(value)) {
                this.value = '';
            } else {
                const maxGrade = parseInt($(this).attr("max"));
                if (value < 0) {
                    this.value = 0;
                } else if (value > maxGrade) {
                    this.value = maxGrade;
                }
            }
            fn.toggleState(e.target);
        });
    },

    validateNumber: function(event) {
        const key = window.event ? event.keyCode : event.which;
        return !(key > 31 && (key < 48 || key > 57));
    },

    toggleState: function(element) {
        let gradeWrapper;
        if ( element.nodeName.toLowerCase() === 'input' ) {
            gradeWrapper = element;
        } else if (element.nodeName.toLowerCase() === 'select') {
            gradeWrapper = element.parentElement;
        }
        let classes = gradeWrapper.classList;
        if (element.value !== element.defaultValue) {
            classes.add("__unsaved");
        } else {
            classes.remove("__unsaved");
        }
    },

    assignmentGradeInputIncrementByArrows: function() {
        gradebook.on("keydown", "input.__assignment", function(e) {
            if (e.keyCode === 38 || e.keyCode === 40) {
                let that = this; // input object
                // Mb it's incredibly stupid practice, who cares?
                if (that.increment === undefined || that.decrement === undefined) {
                    that.increment = $.arrowIncrement.prototype.increment;
                    that.decrement = $.arrowIncrement.prototype.decrement;
                }
                that.opts = {
                    // Slightly modified version of original $.arrowIncrement method
                    parseFn: function (value) {
                        const parsed = value.match(/^(\D*?)(\d*(,\d{3})*(\.\d+)?)\D*$/);
                        if (parsed && parsed[2]) {
                            if (parsed[1] && parsed[1].indexOf('-') >= 0) {
                                return -parsed[2].replace(',', '');
                            } else {
                                return +parsed[2].replace(',', '');
                            }
                        }
                        // Empty string as 0
                        if (value.length === 0) {
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

    scrollButtons: function() {
        if (gradebookContainer.width() <= gradebook.width()) {
            scrollButtonsWrapper.on("click", ".scroll.left", function() {
                fn.scroll(-1);
            });
            scrollButtonsWrapper.on("click", ".scroll.right", function() {
                fn.scroll(1);
            });
            scrollButtonsWrapper.css("visibility", "visible");
        }
    },

    scroll: function (xdir) {
        const assignmentColumnWidth = 100;
        const xinc = assignmentColumnWidth * parseInt(xdir);
        if (xinc !== 0) {
            const scrollXOffset = gradebookContainer.scrollLeft();
            gradebookContainer.scrollLeft(scrollXOffset + xinc);
        }
    },

};

export default fn;