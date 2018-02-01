import {showComponentError} from 'utils';
import "magnific-popup";

import styles from 'scss/club/style.scss';

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
