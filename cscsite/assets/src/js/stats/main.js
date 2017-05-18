import $ from 'jquery';
// TODO: How to deal with global variables like window.URLS? I want to import them explicitly.

import ParticipantsYear from './plots/ParticipantsYear.js';
import ParticipantsGroup from './plots/ParticipantsGroup.js';
import AssignmentsProgress from './plots/AssignmentsProgress.js';
import AssignmentsDeadline from './plots/AssignmentsDeadline.js';
import AssignmentsResults from './plots/AssignmentsResults.js';
import AssignmentsScore from './plots/AssignmentsScore.js';
import EnrollmentsResults from './plots/EnrollmentsResults.js';
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

    renderPlots: function (courseSessionId) {
        // Prepare templates
        let filterGenderTpl = template(document.getElementById(
                "plot-filter-gender-template").innerHTML),
            filterIsOnlineTpl = template(document.getElementById(
                "plot-filter-is-online-template").innerHTML),
            filterCurriculumYearTpl = template(document.getElementById(
                "plot-filter-curriculum_year-template").innerHTML),
            filterSubmitButtonTpl = template(document.getElementById(
                "plot-filter-submit-button").innerHTML);
        // Participants
        let options = {
            course_session_id: courseSessionId,
            apiRequest: ParticipantsYear.getStats(courseSessionId)
        };
        new ParticipantsYear('#plot-participants-by-year', options);
        new ParticipantsGroup('#plot-participants-by-group', options);
        // Assignments
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