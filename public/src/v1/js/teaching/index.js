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
    }
});