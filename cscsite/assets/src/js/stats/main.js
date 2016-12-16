import ParticipantsYear from './plots/ParticipantsYear.js';
import ParticipantsGroup from './plots/ParticipantsGroup.js';
import AssignmentsProgress from './plots/AssignmentsProgress.js';
import AssignmentsDeadline from './plots/AssignmentsDeadline.js';
import AssignmentsPerformance from './plots/AssignmentsPerformance.js';

$(document).ready(function () {
    // DOM elements here
    let termFilter = $('#term-filter');
    let courseFilter = $('#course-filter');

    window.test = new ParticipantsYear('#plot-participants-by-year',
        json_data.course_session_id);
    // FIXME: лишний ajax-запрос. ВЕЗДЕ)
    new ParticipantsGroup('#plot-participants-by-group',
        json_data.course_session_id);

    new AssignmentsProgress('#plot-assignments-progress',
        json_data.course_session_id);

    new AssignmentsDeadline('#plot-assignments-deadline',
        json_data.course_session_id);

    new AssignmentsPerformance('#plot-assignments-performance',
        json_data.course_session_id);

    // TODO: refactor
    // TODO: Как обозначать состояние кнопки "Фильтровать", если данные изменились/устарели?
    termFilter.on('change', function () {
        let term_id = $(this).val();
        let courses = json_data.courses[term_id];
        courseFilter.empty();
        courses.forEach(function (co) {
            let opt = document.createElement('option');
            opt.value = co['pk'];
            opt.innerHTML = co['course__name'];
            $('#course-filter').get(0).appendChild(opt);
        });
        courseFilter.selectpicker('refresh');
    });

    // TODO: добавить обработчик submit'а формы и пока просто пропускать запрос. Потом вроде как надо научиться пересобирать все графики (они сами должны делать ajax-запросы)
});