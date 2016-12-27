import * as d3 from "d3";
// TODO: Also, used global c3, URLS, jQuery. Investigate how to import them explicitly

class AssignmentsScore {
    i18n = {
        lang: 'ru',
        ru: {
            no_assignments: "Заданий не найдено.",
            lines: {
                pass: "Проходной балл",
                mean: "Средний балл",
                max: "Максимальный балл"
            }
        }
    };

    constructor(id, options) {
        this.id = id;
        this.type = 'bar';
        this.data = {};
        this.plot = undefined;

        let promise = options.apiRequest ||
                      this.getStats(options.course_session_id);
        promise
            .then(this.convertData)
            .done(this.render);
    }

    static getStats(course_session_id) {
        let dataURL = URLS["api:stats_assignments"](course_session_id);
        return $.getJSON(dataURL);
    }

    convertData = (jsonData) => {
        console.log(jsonData);
        let titles = [],
            rows = [[this.i18n.ru.lines.pass, this.i18n.ru.lines.mean,
                this.i18n.ru.lines.max]];

        jsonData.forEach((assignment) => {
            titles.push(assignment.title);
            let sum = 0,
                cnt = 0;
            // Looks complicated to use Array.prototype.filter
            assignment.assigned_to.forEach((student) => {
                if (student.grade !== null) {
                    sum += student.grade;
                    cnt += 1;
                }
            });
            let mean = (cnt === 0) ? 0 : (sum / cnt).toFixed(1);
            rows.push([assignment.grade_min, mean, assignment.grade_max]);
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
                rows: data.rows
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
            legend: {
                position: 'right'
            },
            grid: {
                y: {
                    show: true
                }
            },
        });
    };
}

export default AssignmentsScore;