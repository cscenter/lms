import ParticipantsYear from './plots/ParticipantsYear.js';
import ParticipantsGroup from './plots/ParticipantsGroup.js';
import AssignmentsProgress from './plots/AssignmentsProgress.js';
import AssignmentsDeadline from './plots/AssignmentsDeadline.js';
import AssignmentsResults from './plots/AssignmentsResults.js';
import AssignmentsMeanScore from './plots/AssignmentsMeanScore.js';
import EnrollmentsResults from './plots/EnrollmentsResults.js';
import {getTemplate} from 'stats/utils';

// DOM elements
let termFilter = $('#term-filter');
let courseFilter = $('#course-filter');
let courseFilterForm = $('#courses-filter-form');

 function renderPlots (courseSessionId) {
    // Participants
    let options = { course_session_id: courseSessionId };
    new ParticipantsGroup('plot-participants-by-group', options);
    new ParticipantsYear('plot-participants-by-year', options);
    // Assignments
     options = {
        course_session_id: courseSessionId,
        templates: {
            filters: {
                gender: getTemplate("plot-filter-gender-template"),
                curriculumYear: getTemplate("plot-filter-curriculum_year-template"),
                select: getTemplate("plot-filter-select-template"),
                isOnline: getTemplate("plot-filter-is-online-template"),
                submitButton: getTemplate("plot-filter-submit-button")
            }
        },
        apiRequest: AssignmentsProgress.getStats(courseSessionId)
    };
    new AssignmentsProgress('plot-assignments-progress', options);
    new AssignmentsDeadline('plot-assignments-deadline', options);
    new AssignmentsResults('plot-assignments-results', options);
    new AssignmentsMeanScore('plot-assignments-score', options);
    // Enrollments
    new EnrollmentsResults('plot-enrollments-results',
        courseSessionId);
}

function initFilter() {
    courseFilter.on('change', function () {
        $('button[type=submit]', courseFilterForm).removeAttr('disabled');
    });
    // TODO: refactor
    termFilter.on('change', function () {
        let term_id = $(this).val();
        let courses = jsonData.courses[term_id];
        courseFilter.empty();
        courses.forEach(function (co) {
            let opt = document.createElement('option');
            opt.value = co['pk'];
            opt.innerHTML = `${co['meta_course__name']}`;
            courseFilter.get(0).appendChild(opt);
        });
        courseFilter.selectpicker('refresh');
        $('button[type=submit]', courseFilterForm).removeAttr('disabled');
    });
}

export function initPlots() {
    let courseSessionId = jsonData.course_session_id;
    initFilter();
    renderPlots(courseSessionId);
}