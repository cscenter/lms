import * as d3 from "d3";
// TODO: Also, used global c3, URLS, jQuery. Investigate how to import them explicitly

class ParticipantsYear {

    i18n = {
        ru: {
            diagram: "Диаграмма",
            plot: "График",
            students: ""
        }
    };

    constructor(id, options) {
        console.log("ParticipantsYear options", options);
        this.id = id;
        this.type = 'pie';
        // FIXME: move to state
        this.data = {};
        this.plot = c3.generate({
            bindto: this.id,
            grid: {
                y: {
                    show: true
                }
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
            data: {
                type: this.type,
                columns: []
            },
            // legend: {
            //     position: 'right'
            // }
        });
        // Switch plot type button
        let buttons = [
            {name: this.i18n.ru.diagram, callback: this.renderPieChart},
            {name: this.i18n.ru.plot, callback: this.renderBarChart}
        ];
        // FIXME: Если всё время вызывать generate, то лучше перенести кнопки из графика...
        d3.select(this.id).insert('div', ":first-child")
            .attr('class', 'btn-group pull-right')
            .attr('role', 'group')
            .attr('aria-label', 'Toggle')
            .selectAll('button')
            .data(buttons)
            .enter().append('button').attr('class', 'btn btn-default')
            .attr('data-id', id => id)
            .text(d => d.name)
            .on('click',  (d) => {
                d.callback();
            });

        let promise = options.apiRequest ||
                      this.getStats(options.course_session_id);
        promise
            .then(this.convertData)
            .done(this.renderPieChart);
    }

    static getStats(course_session_id) {
        let dataURL = URLS["api:stats_participants"](course_session_id);
        return $.getJSON(dataURL);
    }

    convertData = (jsonData) => {
        let data = {};
        jsonData.forEach(function (e) {
            if (!(e.curriculum_year in data)) {
                data[e.curriculum_year] = 0;
            }
            data[e.curriculum_year] += 1;
        });
        this.data = data;
        // FIXME: по-моему я это уже не юзаю!
        let columns = [];
        for (let key in data) {
            columns.push([key, data[key]]);
        }
        return columns;
    }

    dataForPie() {
        let columns = [];
        for (let key in this.data) {
            columns.push([key, this.data[key]]);
        }
        return columns;
    }

    dataForLine() {
        let x = ['year'],
            y = ['students'];
        for (let key in this.data) {
            x.push(key);
            y.push(this.data[key]);
        }
        return [x, y];
    }

    loadData(columns) {

    }

    renderPieChart = () => {
        this.type = 'pie';
        this.plot.load({
            type: this.type,
            columns: this.dataForPie(),
            unload: true
        });
    };

    renderBarChart = () => {
        if (this.type == 'bar') {
            return;
        }
        this.type = 'bar';
        this.plot.load({
            type: this.type,
            xs: { 'students': 'year'},
            xFormat: '%Y',
            x: 'year',
            columns: this.dataForLine(),
            names: {
                students: this.i18n.ru.students
            },
            unload: true
        });
        this.plot.legend.hide();
    };
}

export default ParticipantsYear;