import initApplicantDetailSection from './applicant_detail';
import initApplicantListSection from './applicant_list';
import initInterviewSection from './interview';
import {showComponentError, getSections} from 'utils';
import {TIMEPICKER_ICONS, TIMEPICKER_TOOLTIPS} from "conf";


$(document).ready(function () {
    let sections = getSections();
    if (sections.includes("applicant_list")) {
        initApplicantListSection();
    }
    if (sections.includes("applicant")) {
        initApplicantDetailSection();
    }
    if (sections.includes("interview")) {
        initInterviewSection();
    }
});

$(document).ready(function () {
    let sections = getSections();
    if (sections.includes("datetimepicker")) {
        $('[data-toggle="tooltip"]').tooltip();
        // TODO: Move to `interview_list`
        import('forms')
            .then(_ => {
                // Status
                $('select[name="status"]').selectpicker({
                    iconBase: 'fa',
                    tickIcon: 'fa-check'
                });
                $('select[name="status"]').on('loaded.bs.select', function (e) {
                    $(e.target).selectpicker('setStyle', 'btn-default');
                });
                // Date range
                $('.input-daterange .input-group, #id_date').datetimepicker({
                    allowInputToggle: true,
                    useCurrent: false,
                    locale: 'ru',
                    format: 'DD.MM.YYYY',
                    stepping: 5,
                    toolbarPlacement: "bottom",
                    keyBinds: {
                        left: false,
                        right: false,
                        escape: function () {
                            this.hide();
                        },
                    },
                    icons: TIMEPICKER_ICONS,
                    tooltips: TIMEPICKER_TOOLTIPS,

                });
                let dateFromPicker = $('#id_date_0').closest('.input-group');
                let dateToPicker = $('#id_date_1').closest('.input-group');
                dateToPicker.data("DateTimePicker").useCurrent(false);
                dateFromPicker.on("dp.change", function (e) {
                    dateToPicker.data("DateTimePicker").minDate(e.date);
                    if (e.date) {
                        if (dateToPicker.data("DateTimePicker").date() === null) {
                            dateToPicker.data("DateTimePicker").defaultDate(e.date);
                        } else if (dateToPicker.data("DateTimePicker").date() < e.date) {
                            dateToPicker.data("DateTimePicker").date(e.date);
                        }
                    }
                });
                dateToPicker.on("dp.change", function (e) {
                    dateFromPicker.data("DateTimePicker").maxDate(e.date);
                    if (dateFromPicker.data("DateTimePicker").date() === null) {
                        dateFromPicker.data("DateTimePicker").defaultDate(e.date);
                    }
                });
            })
            .catch(error => showComponentError(error));
    }
});