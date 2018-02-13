import {showComponentError} from 'utils';

// this line is a workaround for chunk hasher, remove it later
$(document).ready(function () {
    let section = $("body").data("init-section");
    if (section === "gradebook") {
        import(/* webpackChunkName: "gradebook" */ 'teaching/gradebook')
            .then(module => {
                const component = module.default;
                component.launch();
            })
            .catch(error => showComponentError(error));
    } else if (section === "submissions") {
        import(/* webpackChunkName: "submissions" */ 'teaching/submissions')
            .then(m => {
                const component = m.default;
                component.launch();
            })
            .catch(error => showComponentError(error));
    }
});
