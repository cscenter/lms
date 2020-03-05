import $ from 'jquery';
import "bootstrap-select/js/bootstrap-select";
import "bootstrap-select/js/i18n/defaults-ru_RU";
import {initPlots as initLearningStats}  from './learning/main';
import {initPlots as initAdmissionStats}  from './admission/main';

const statsPage = $('#stats-page');

$(function() {
    const entryPoint = statsPage.data('entry');
    if (entryPoint === 'learning') {
        initLearningStats();
    } else if (entryPoint === 'admission') {
        initAdmissionStats();
    }
});
