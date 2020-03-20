import "bootstrap-select/js/bootstrap-select";
import "bootstrap-select/js/i18n/defaults-ru_RU";
import moment from "moment";
import "moment/locale/ru";
import "eonasdan-bootstrap-datetimepicker";
import(/* webpackChunkName: "bootstrap-datetimepicker" */ 'eonasdan-bootstrap-datetimepicker/build/css/bootstrap-datetimepicker.min.css');


$.fn.selectpicker.Constructor.BootstrapVersion = '3';

export const TIMEPICKER_ICONS = {
    time: 'fa fa-clock-o',
    date: 'fa fa-calendar',
    up: 'fa fa-chevron-up',
    down: 'fa fa-chevron-down',
    previous: 'fa fa-chevron-left',
    next: 'fa fa-chevron-right',
    today: 'fa fa-screenshot',
    clear: 'fa fa-trash',
    close: 'fa fa-check',
};

export const TIMEPICKER_TOOLTIPS = {
    today: 'Go to today',
    clear: 'Clear selection',
    close: 'Закрыть',
    selectMonth: 'Выбрать месяц',
    prevMonth: 'Предыдущий месяц',
    nextMonth: 'Следующий месяц',
    selectYear: 'Выбрать год',
    prevYear: 'Предыдущий год',
    nextYear: 'Следующий год',
    selectDecade: 'Выбрать декаду',
    prevDecade: 'Предыдущая декада',
    nextDecade: 'Следующая декада',
    prevCentury: 'Предыдущий век',
    nextCentury: 'Следующий век'
};


export function initDatePickers() {
    $('.datepicker').datetimepicker({
        allowInputToggle: true,
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
}

export function initTimePickers() {
    $('.timepicker').datetimepicker({
        locale: 'ru',
        format: 'HH:mm',
        stepping: 5,
        useCurrent: false,
        icons: TIMEPICKER_ICONS,
        defaultDate: new Date("01/01/1980 18:00"),
        allowInputToggle: true,
        tooltips: TIMEPICKER_TOOLTIPS,
        keyBinds: {
            left: false,
            right: false,
        }
    });
}

export function initMultiSelectPickers() {
    document.querySelectorAll('.multiple-select').forEach((element) => {
        $(element).selectpicker({
            iconBase: 'fa',
            tickIcon: 'fa-check',
        });
    });
}
