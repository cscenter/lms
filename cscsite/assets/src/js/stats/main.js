import $ from 'jquery';
// TODO: How to deal with global variables like window.URLS? I want to import them explicitly in

import ParticipantsYear from './learning/plots/ParticipantsYear.js';
import ParticipantsGroup from './learning/plots/ParticipantsGroup.js';
import AssignmentsProgress from './learning/plots/AssignmentsProgress.js';
import AssignmentsDeadline from './learning/plots/AssignmentsDeadline.js';
import AssignmentsResults from './learning/plots/AssignmentsResults.js';
import AssignmentsScore from './learning/plots/AssignmentsScore.js';
import EnrollmentsResults from './learning/plots/EnrollmentsResults.js';
let template = require('lodash.template');

// Filter DOM elements here
let termFilter = $('#term-filter'),
    courseFilter = $('#course-filter'),
    courseFilterForm = $('#courses-filter-form');

let fn = {
    init: function () {
        let courseSessionId = json_data.course_session_id;
        fn.renderPlots(courseSessionId);
        fn.initCoursesFilter()
    },

    getTemplate: function (id) {
        return template(document.getElementById(id).innerHTML);
    },

    renderPlots: function (courseSessionId) {
        // Participants
        let options = { course_session_id: courseSessionId };
        new ParticipantsGroup('#plot-participants-by-group', options);
        new ParticipantsYear('#plot-participants-by-year', options);
        // Assignments
        const filterGenderTpl = fn.getTemplate("plot-filter-gender-template");
        const filterIsOnlineTpl = fn.getTemplate("plot-filter-is-online-template");
        const filterCurriculumYearTpl = fn.getTemplate("plot-filter-curriculum_year-template");
        const filterSubmitButtonTpl = fn.getTemplate("plot-filter-submit-button");
        options = {
            course_session_id: courseSessionId,
            templates: {
                filters: {
                    gender: filterGenderTpl,
                    curriculumYear: filterCurriculumYearTpl,
                    isOnline: filterIsOnlineTpl,
                    submitButton: filterSubmitButtonTpl
                }
            },
            apiRequest: AssignmentsProgress.getStats(courseSessionId)
        };
        new AssignmentsProgress('plot-assignments-progress', options);
        new AssignmentsDeadline('plot-assignments-deadline', options);
        new AssignmentsResults('plot-assignments-results', options);
        new AssignmentsScore('plot-assignments-score', options);
        // Enrollments
        new EnrollmentsResults('#plot-enrollments-results',
            courseSessionId);
    },

    initCoursesFilter: function () {
        courseFilter.on('change', function () {
            $('button[type=submit]', courseFilterForm).removeAttr('disabled');
        });
        // TODO: refactor
        termFilter.on('change', function () {
            let term_id = $(this).val();
            let courses = json_data.courses[term_id];
            courseFilter.empty();
            courses.forEach(function (co) {
                let opt = document.createElement('option');
                opt.value = co['pk'];
                opt.innerHTML = co['course__name'];
                courseFilter.get(0).appendChild(opt);
            });
            courseFilter.selectpicker('refresh');
            $('button[type=submit]', courseFilterForm).removeAttr('disabled');
        });
    }
};

$(document).ready(function () {
    fn.init();
});