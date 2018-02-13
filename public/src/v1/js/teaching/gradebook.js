// TODO: remove arrow-increment
import SweetAlert from "bootstrap-sweetalert";

const buttonDownloadCSV = $(".marks-sheet-csv-link");

let submitButton = $('#marks-sheet-save');

let gradebookContainer = $("#gradebook-container");

let gradebook = $("#gradebook");

let scrollButtonsWrapper = $(".gradebook__controls");

function isChanged(element) {
    return element.value !== element.getAttribute("initial");
}

const fn = {
    launch: function () {
        fn.restoreStates();
        fn.finalGradeSelects();
        fn.submitForm();
        fn.downloadCSVButton();
        // fn.assignmentGradeInputValidator();
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
        // submitButton.removeAttr("disabled");

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