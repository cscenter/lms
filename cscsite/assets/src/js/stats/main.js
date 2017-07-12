import $ from 'jquery';
import {init as initLearningStats}  from './learning/main';
import {init as initAdmissionStats}  from './admission/main';
// TODO: How explicitly import global variables like window.URLS and json_data?

const statsPage = $('#stats-page');

let fn = {
    init: function () {
        const entryPoint = statsPage.data('entry');
        if (entryPoint === 'learning') {
            initLearningStats();
        } else if (entryPoint === 'admission') {
            initAdmissionStats();
        }
        // TODO: Сейчас есть проблема - все тяжеловесные библиотеки типа d3/c3 будут перетекать в чанки
        // Если и использовать их - то только разобравшись, как засунуть их в родительский модуль.
        // import(/* webpackChunkName: "_stats_courses" */ './learning/main').then(module => {
        //     module.init();
        // });
    },
};

$(document).ready(function () {
    fn.init();
});