import * as d3 from "d3";
import * as moment from 'moment';
// TODO: Also, used global c3, URLS, jQuery, moment.js. Investigate how to import them explicitly

class AssignmentsPerformance {
    i18n = {
        lang: 'ru',
        ru: {
            no_assignments: "Заданий не найдено.",
            // TODO: Load from backend?
            states: {
                not_submitted: "Не отправлено",
                not_checked: "Не проверено",
                unsatisfactory: "Незачет",
                pass: "Удовлетворительно",
                good: "Хорошо",
                excellent: "Отлично"
            }
        }
    };

    constructor(id, course_session_id) {
        this.id = id;
        this.type = 'bar';
        this.data = {};
        this.plot = undefined;

        // Order is unspecified for Object, but I believe browsers sort
        // it in a proper way
        this.states = Object.keys(this.i18n.ru.states).reduce((m, k) => {
            return m.set(k, this.i18n.ru.states[k]);
        }, new Map());

        this.loadStats(course_session_id)
            .done(this.render);
    }

    loadStats(course_session_id) {
        return this.getJSON(course_session_id)
                   .then(this.convertData);
    }

    getJSON(course_session_id) {
        let dataURL = URLS["api:stats_assignments"](course_session_id);
        return $.getJSON(dataURL);
    }

    convertData = (jsonData) => {
        console.log("performance ", jsonData);
        let states = Array.from(this.states, ([k, v]) => v),
            titles = [],
            rows = [states];

        jsonData.forEach((assignment) => {
            titles.push(assignment.title);
            let counters = states.reduce(function (a, b) {
                    return a.set(b, 0);
                }, new Map());
            assignment.assigned_to.forEach((student) => {
                let state = this.states.get(student.state);
                counters.set(state, counters.get(state) + 1);
            });
            rows.push(Array.from(counters, ([k, v]) => v));
        });

        this.data = {
            titles: titles,  // assignment titles
            rows: rows
        };
        console.debug("performance data", this.data);
        return this.data;
    };

    render = (data) => {
        if (!data.titles.length) {
            $(this.id).html(this.i18n.ru.no_assignments);
            return;
        }

        // Let's generate here, a lot of troubles with c3.load method right now
        console.log(data);
        this.plot = c3.generate({
            bindto: this.id,
            data: {
                type: this.type,
                rows: data.rows,
            },
            tooltip: {
                format: {
                    title: function (d) { return data.titles[d]; },
                }
            },
            axis: {
              x: {
                tick: {
                  format: function (x) { return x + 1; }
                }
              }
            },
            grid: {
                y: {
                    show: true
                }
            },
        });
    };
}

export default AssignmentsPerformance;