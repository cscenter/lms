import {showComponentError, getSections} from 'utils';

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
    }
});
