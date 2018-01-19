import "holderjs";
import "jquery-lazyload";

const fn = {
    launch: function () {
        $("img.lazy").lazyload({});
    },
};

export default fn;