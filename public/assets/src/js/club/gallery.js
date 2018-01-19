const fn = {
    launch: function () {
        $('.gallery a').magnificPopup({
            type:'image',
            image: {
                titleSrc: function(item) {
                    return item.el.attr('title');
                }
            },
            gallery: {
                enabled: true,
                tCounter: '<span class="mfp-counter">%curr% из %total%</span>'
            },
            disableOn: 400,
            key: 'teacher-gallery',
        });
    },
};

export default fn;

