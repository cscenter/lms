import * as d3 from "d3";
// TODO: Also, used global c3, URLS, jQuery. Investigate how to import them explicitly

class ParticipantsGroup {

    i18n = {
        ru: {
            groups: {
                STUDENT_CENTER: "Студент центра",
                VOLUNTEER: "Вольнослушатель",
                GRADUATE: "Выпускник"
            },
            total_participants: "Всего слушателей курса"
        }
    };

    constructor(id, course_session_id) {
        this.id = id;
        this.type = 'pie';
        // TODO: load from backend?
        this.groups = {
            1: this.i18n.ru.groups.STUDENT_CENTER,
            4: this.i18n.ru.groups.VOLUNTEER,
            3: this.i18n.ru.groups.GRADUATE
        };
        // FIXME: move to state?
        this.data = {};
        this.plot = c3.generate({
            bindto: this.id,
            tooltip: {
                format: {
                    value: (value, ratio, id) => {
                        return value + '&nbsp;чел.';
                    }
                }
            },
            data: {
                type: this.type,
                columns: []
            },
            // legend: {
            //     position: 'right'
            // }
        });

        this.loadStats(course_session_id)
            .then(this.render)
            .done(this.appendParticipantsInfo);

    }

    appendParticipantsInfo = () => {
        let total = Object.values(this.data).reduce(function (a, b) {
            return a + b;
        }, 0);

        d3.select(this.id).insert('div', ":first-child")
            .attr('class', 'info')
            .selectAll('div')
            .data([total])
            .enter()
            .append('div')
            .text(d => this.i18n.ru.total_participants + ': ' + d);
    };

    loadStats(course_session_id) {
        return this.getJSON(course_session_id)
                   .then(this.convertData);
    }

    getJSON(course_session_id) {
        let dataURL = URLS["api:stats_participants"](course_session_id);
        return $.getJSON(dataURL);
    }

    convertData = (jsonData) => {
        let data = Object.keys(this.groups).reduce(function(a, b) {
          a[b] = 0; return a;
        }, {});

        // TODO: если у студента обе группы случайно? Это увеличит общее кол-во участников, что плохо
        // TODO: если нет групп у студента?
        jsonData.forEach(function (student) {
            student.groups.forEach(function (group) {
                if (group in data) {
                    data[group] += 1;
                }
            });
        });
        console.log(data);
        this.data = data;
        let columns = [];
        for (let key in data) {
            if (key != 3 || data[key] != 0) {
                columns.push([this.groups[key], data[key]]);
            }
        }
        console.log(columns);
        return columns;
    };

    render = (columns) => {
        this.type = 'pie';
        this.plot.load({
            type: this.type,
            columns: columns,
            unload: true
        });
    };
}

export default ParticipantsGroup;