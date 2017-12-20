import "vendor/jquery.arrow-increment.min"
import SweetAlert from "bootstrap-sweetalert";

const buttonDownloadCSV = $(".marks-sheet-csv-link");

let submitButton = $('#marks-sheet-save');

let gradebookContainer = $("#gradebook-container");

let gradebook = $("#gradebook");

let scrollButtonsWrapper = $(".gradebook__controls");

function validateNumber(event) {
    const key = window.event ? event.keyCode : event.which;
    return !(key > 31 && (key < 48 || key > 57));
}

function isChanged(element) {
    return element.value !== element.getAttribute("initial");
}

const fn = {
    launch: function () {
        fn.restoreStates();
        fn.finalGradeSelects();
        fn.submitForm();
        fn.downloadCSVButton();
        fn.assignmentGradeInputValidator();
        fn.assignmentGradeInputIncrementByArrows();
        fn.scrollButtons();
    },

    /**
     * If browser supports html5 `autocomplete` attribute,
     * we can accidentally hide unsaved state on page reload.
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

    submitForm: function () {
        // Form heavily relies on js-behavior. `Disabled` default state
        // prevents accidental submission if js is not activated.
        submitButton.removeAttr("disabled");

        $("form[name=gradebook]").submit(function(e) {
            let elements = this.querySelectorAll('.__input, .__final_grade select');
            Array.prototype.forEach.call(elements, function (element) {
                if (!isChanged(element)) {
                    element.disabled = true;
                    const inputQuery = `input[name=initial-${element.name}]`;
                    document.querySelector(inputQuery).disabled = true;
                }
            });
        });
    },

    finalGradeSelects: function() {
        gradebook.on("change", "select", function (e) {
            fn.toggleState(e.target);
        });
    },

    assignmentGradeInputValidator: function() {
        gradebook.on("keypress", "input.__assignment", validateNumber);
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

    toggleState: function(element) {
        let wrapper;
        if ( element.nodeName.toLowerCase() === 'input' ) {
            wrapper = element;
        } else if (element.nodeName.toLowerCase() === 'select') {
            wrapper = element.parentElement;
        }
        if (isChanged(element)) {
            wrapper.classList.add("__unsaved");
        } else {
            wrapper.classList.remove("__unsaved");
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