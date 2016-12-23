import * as d3 from "d3";
// TODO: Also, used global c3, URLS, jQuery. Investigate how to import them explicitly

class EnrollmentsResults {
    i18n = {
        lang: 'ru',
        ru: {
            no_enrollments: "Студенты не найдены.",
            grades: {
                not_graded: "Без оценки",
                unsatisfactory: "Незачет",
                pass: "Удовлетворительно",
                good: "Хорошо",
                excellent: "Отлично"
            }
        }
    };

    constructor(id, course_session_id) {
        this.id = id;
        this.type = 'pie';
        this.data = {};
        this.plot = undefined;

        this.grades = Object.keys(this.i18n.ru.grades).reduce((m, k) => {
            return m.set(k, this.i18n.ru.grades[k]);
        }, new Map());

        this.loadStats(course_session_id)
            .done(this.render);
    }

    loadStats(course_session_id) {
        return this.getJSON(course_session_id)
                   .then(this.convertData);
    }

    getJSON(course_session_id) {
        let dataURL = URLS["api:stats_enrollments"](course_session_id);
        return $.getJSON(dataURL);
    }

    convertData = (jsonData) => {
        let data = {};
        jsonData.forEach(function (e) {
            if (!(e.grade in data)) {
                data[e.grade] = 0;
            }
            data[e.grade] += 1;
        });
        this.data = data;
        let columns = [];
        for (let key in data) {
            console.log(this.grades, key);
            columns.push([this.grades.get(key), data[key]]);
        }
        return columns;
    }

    render = (data) => {
        if (!data.length) {
            $(this.id).html(this.i18n.ru.no_enrollments);
            return;
        }

        // Let's generate here, a lot of troubles with c3.load method right now
        console.log(data);
        this.plot = c3.generate({
            bindto: this.id,
            data: {
                type: this.type,
                columns: data
            },
            tooltip: {
                format: {
                    value: (value, ratio, id)  => {
                        if (this.type == 'pie') {
                            return value + '&nbsp;чел.';
                        } else {
                            return value;
                        }
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

export default EnrollmentsResults;