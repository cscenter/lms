import {showComponentError, getSections} from 'utils';

$(document).ready(function () {
    let sections = getSections();
    if (sections.includes("tooltips")) {
        let defaultWhiteList = $.fn.tooltip.Constructor.DEFAULTS.whiteList;
        defaultWhiteList.dl = ['class'];
        defaultWhiteList.dd = [];
        defaultWhiteList.dt = [];
        $('[data-toggle="tooltip"]').tooltip();
    }
    if (sections.includes("datetimepickers")) {
        import('components/forms')
            .then(m => {
                m.initDatePickers();
                m.initTimePickers();
            })
            .catch(error => showComponentError(error));
    }
    if (sections.includes("selectpickers")) {
        import('components/forms')
            .then(m => {
                m.initMultiSelectPickers();
            })
            .catch(error => showComponentError(error));
    }

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
    } else if (sections.includes("courseClassForm")) {
        // FIXME: omg, what is this? remove?
        let ends_at_touched = false;
        // FIXME: use .on here
        $("#id_ends_at").focus(function () {
            ends_at_touched = true;
        });

        // this is fragile as hell, didn't find a suitable library
        $("#id_starts_at").change(function () {
            var DELTA_MINUTES = 80;

            function pad(num, size) {
                var s = num + "";
                while (s.length < size) s = "0" + s;
                return s;
            }

            if (!ends_at_touched) {
                const string_time = $(this).val();
                var matches = string_time.match(
                    "([0-9]{2})([:\-])([0-9]{2})([:0-9\-]*)");
                if (matches !== null) {
                    var hours = parseInt(matches[1]);
                    var separator = matches[2];
                    var minutes = parseInt(matches[3]);
                    var maybe_seconds = matches[4];

                    var raw_new_minutes = minutes + DELTA_MINUTES;
                    var new_hours = (hours + Math.floor(raw_new_minutes / 60)) % 24;
                    var new_minutes = raw_new_minutes % 60;

                    $("#id_ends_at").val(pad(new_hours, 2)
                        + separator
                        + pad(new_minutes, 2)
                        + maybe_seconds);
                } else {
                    console.warning("Can't parse " + string_time);
                }
            }
        });
    }
});