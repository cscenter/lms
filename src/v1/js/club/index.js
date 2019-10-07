import {showComponentError} from 'utils';
import "magnific-popup";

$(document).ready(function () {
    const section = $("body").data("init-section");
    if (section === "gallery") {
        import(/* webpackChunkName: "gallery" */ 'club/gallery')
            .then(m => {
                const component = m.default;
                component.launch();
            })
            .catch(error => showComponentError(error));
    }
});
