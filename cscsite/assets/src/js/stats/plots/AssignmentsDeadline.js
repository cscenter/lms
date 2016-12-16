import * as d3 from "d3";
import * as moment from 'moment';
// TODO: Also, used global c3, URLS, jQuery, moment.js. Investigate how to import them explicitly

class AssignmentsDeadline {
    i18n = {
        lang: 'ru',
        ru: {
            no_assignments: "Заданий не найдено.",
            types: {
                after: "После дедлайна",
                lt3hours: "Менее 3 часов",
                lte3to24hours: "3-24 часа",
                lte1to6days: "1-6 дней",
                gte7days: "7 дней и более",
                no_submission: "Не сдавал"
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
        this.types = Object.keys(this.i18n.ru.types).reduce((m, k) => {
            return m.set(k, this.i18n.ru.types[k]);
        }, new Map());

        this.loadStats(course_session_id)
            .done(this.render);
    }

    // Convert diff between first submission and deadline to plot column type
    toType(deadline_at, submitted_at) {
        if (submitted_at === null) {
            return this.types.get("no_submission");
        }
        let diff_ms = deadline_at - new Date(submitted_at);
        if (diff_ms <= 0) {
            return this.types.get("after");
        } else {
            let diff = new moment.duration(diff_ms),
                inDays = diff.asDays();
            if (inDays >= 7) {
                return this.types.get("gte7days");
            } else if (inDays >= 1) {
                return this.types.get("lte1to6days");
            } else {
                let inHours = diff.asHours();
                if (inHours >= 3) {
                    // FIXME: не понятно, куда отнести 24й час
                    return this.types.get("lte3to24hours");
                } else {
                    return this.types.get("lt3hours");
                }
            }
        }
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
        console.log(jsonData);
        let types = Array.from(this.types, ([k, v]) => v),
            titles = [],
            rows = [types];
        console.log("convertData this", this);
        jsonData.forEach((assignment) => {
            titles.push(assignment.title);
            let deadline = new Date(assignment.deadline_at),
                counters = types.reduce(function (a, b) {
                    return a.set(b, 0);
                }, new Map());
            assignment.assigned_to.forEach((student) => {
                let type = this.toType(deadline, student.first_submission_at);
                counters.set(type, counters.get(type) + 1);
            });
            rows.push(Array.from(counters, ([k, v]) => v));
        });

        this.data = {
            titles: titles,
            rows: rows
        };
        console.debug(this.data);
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
                groups: [
                    Array.from(this.types, ([k, v]) => v)
                ]
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
            color: {
                pattern: ['#1f77b4', '#ff7f0e', '#ffbb78', '#2ca02c', '#d62728',  '#9467bd', '#c5b0d5', '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d', '#17becf', '#9edae5']
            },
            legend: {
                position: 'right'
            },
        });
    };
}

export default AssignmentsDeadline;