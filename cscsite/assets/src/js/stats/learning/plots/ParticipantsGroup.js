import * as d3 from "d3";
import * as c3 from "c3";
import $ from 'jquery';

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

    constructor(id, options) {
        this.id = id;
        this.type = 'pie';
        // TODO: load from backend?
        this.groups = {
            1: this.i18n.ru.groups.STUDENT_CENTER,
            4: this.i18n.ru.groups.VOLUNTEER,
            3: this.i18n.ru.groups.GRADUATE
        };
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
                columns: [],
                order: null, // https://github.com/c3js/c3/issues/1945
            }
        });
        let promise = options.apiRequest ||
                      this.constructor.getStats(options.course_session_id);
        promise
            .then(this.convertData)
            .then(this.render)
            .done(this.appendParticipantsInfo);

    }

    static getStats(course_session_id) {
        let dataURL = window.URLS["api:stats_learning_participants"](course_session_id);
        return $.getJSON(dataURL);
    }

    appendParticipantsInfo = () => {
        let total = Object.keys(this.data).reduce((ini, k)  => {
            return ini + this.data[k];
        }, 0);

        d3.select(this.id).insert('div', ":first-child")
            .attr('class', 'info')
            .selectAll('div')
            .data([total])
            .enter()
            .append('div')
            .text(d => this.i18n.ru.total_participants + ': ' + d);
    };

    convertData = (jsonData) => {
        let data = Object.keys(this.groups).reduce(function(a, b) {
          a[b] = 0; return a;
        }, {});
        // Inaccuracy if student have student and volunteer group or haven't both.
        jsonData.forEach(function (student) {
            student.groups.forEach(function (group) {
                if (group in data) {
                    data[group] += 1;
                }
            });
        });
        this.data = data;
        // Prepare data for plot
        let columns = [];
        for (let key in data) {
            if (key !== 3 || data[key] !== 0) {
                columns.push([this.groups[key], data[key]]);
            }
        }
        console.log(columns);
        return columns;
    };

    render = (columns) => {
        this.plot.load({
            type: this.type,
            columns: columns,
        });
    };
}

export default ParticipantsGroup;