import {showComponentError, getSections} from 'utils';
import {TIMEPICKER_ICONS, TIMEPICKER_TOOLTIPS} from "../conf";

$(document).ready(function () {
    let sections = getSections();
    if (sections.includes("gradebook")) {
        import(/* webpackChunkName: "gradebook" */ 'teaching/gradebook')
            .then(module => {
                const component = module.default;
                component.launch();
            })
            .catch(error => showComponentError(error));
    } else if (sections.includes("submissions")) {
        import(/* webpackChunkName: "submissions" */ 'teaching/submissions')
            .then(m => {
                const component = m.default;
                component.launch();
            })
            .catch(error => showComponentError(error));
    } else if (sections.includes("assignmentForm")) {
        $('[data-toggle="tooltip"]').tooltip();
        let defaultWhiteList = $.fn.tooltip.Constructor.DEFAULTS.whiteList;
        defaultWhiteList.dl = ['class'];
        defaultWhiteList.dd = [];
        defaultWhiteList.dt = [];
        $('.has-popover').popover({
            container: 'body',
            html: true,
            placement: 'auto',
            trigger: 'hover',
            content: function () {
                let helpBlockId = $(this).data('target');
                return $(helpBlockId).html();
            }
        });
        import('forms')
            .then(_ => {
                $('.datepicker').datetimepicker({
                    locale: 'ru',
                    format: 'DD.MM.YYYY',
                    stepping: 5,
                    allowInputToggle: true,
                    toolbarPlacement: "bottom",
                    keyBinds: {
                        left: false,
                        right: false,
                        escape: function () {
                            this.hide();
                        },
                    },
                    icons: TIMEPICKER_ICONS,
                    tooltips: TIMEPICKER_TOOLTIPS
                });

                $('.timepicker').datetimepicker({
                    locale: 'ru',
                    format: 'HH:mm',
                    stepping: 1,
                    useCurrent: false,
                    allowInputToggle: true,
                    icons: TIMEPICKER_ICONS,
                    tooltips: TIMEPICKER_TOOLTIPS,
                    defaultDate: new Date("01/01/1980 23:59"),
                    keyBinds: {
                        left: false,
                        right: false,
                    }
                });
            })
            .catch(error => showComponentError(error));
    } else if (sections.includes("datetimepicker")) {
        $('[data-toggle="tooltip"]').tooltip();
        import('forms')
            .then(_ => {
                $('#div_id_date .input-group').datetimepicker({
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

                $('#div_id_starts_at .input-group, #div_id_ends_at .input-group').datetimepicker({
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
                        up: false,
                        down: false
                    }
                });
            })
            .catch(error => showComponentError(error));
    }
});