import $ from 'jquery';
// TODO: How explicitly import global variables like window.URLS and json_data?


let fn = {
    init: function () {
        // TODO: Сейчас есть проблема - все тяжеловесные библиотеки типа d3/c3 будут перетекать в чанки
        // Если и использовать их - то только разобравшись, как засунуть их в родительский модуль.
        import(/* webpackChunkName: "_stats_courses" */ './learning/main').then(module => {
            module.init();
        });
        import(/* webpackChunkName: "_stats_admission" */ './admission/main').then(module => {
            module.init();
        });
    },
};

$(document).ready(function () {
    fn.init();
});