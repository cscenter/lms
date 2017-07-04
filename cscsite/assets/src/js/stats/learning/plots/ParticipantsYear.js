import * as d3 from "d3";
import * as c3 from "c3";
import $ from 'jquery';

class ParticipantsYear {

    i18n = {
        ru: {
            pieChart: "Круговая",
            barChart: "Гистограмма",
            students: ""
        }
    };

    constructor(id, options) {
        this.id = id;
        this.state = {
            data: {
                type: void 0,
                x : 'x',
                unload: true,
                columns: [],
                order: null, // https://github.com/c3js/c3/issues/1945
            },
            groups: [],
        };
        this.plot = c3.generate({
            bindto: this.id,
            grid: {
                y: {
                    show: true
                }
            },
            tooltip: {
                grouped: false,
                format: {
                    title: () => "",
                    value: (value, ratio, id)  => {
                        return value + '&nbsp;чел.';
                    }
                }
            },
            data: this.state.data,
            oninit: this.renderSwitchButtons
        });

        let promise = options.apiRequest ||
                      this.constructor.getStats(options.course_session_id);
        promise
            .then(this.convertData)
            .done(this.renderPieChart);
    }

    static getStats(course_session_id) {
        let dataURL = window.URLS["api:stats_learning_participants"](course_session_id);
        return $.getJSON(dataURL);
    }

    /**
     *  To use data without convertion both in `line` and `pie` chart we
     *  need something like this:
     *  columns: [
     *       ['2013', 30, 0],
     *       ['2014', 0, 90],
     *       ['x', '2013', '2014'],
     *   ],
     * @returns {Array}
     */
    convertData = (rawJSON) => {
        // year => {total students}
        let data = new Map();
        rawJSON.forEach(function (e) {
            data.set(e.curriculum_year,
                    (data.get(e.curriculum_year) || 0) + 1);
        });
        // Recreate to make sure we will iterate entries sorted by year
        data = new Map([...data.entries()].sort());
        let years = Array.from(data.keys(), e => e.toString());
        this.state.groups = [years];
        this.plot.groups(this.state.groups);
        let columns = [
            ['x'].concat(years)
        ];
        data.forEach((v, k) => {
            let row = new Array(data.size + 1).fill(0);
            row[0] = k.toString();
            row[years.indexOf(row[0]) + 1] = v;
            columns.push(row);
        });
        this.state.data.columns = columns;
    };

    renderPieChart = () => {
        if (this.state.data.type === 'pie') { return; }
        this.state.data.type = 'pie';
        this.plot.load(this.state.data);
    };

    renderBarChart = () => {
        if (this.state.data.type === 'bar') { return; }
        this.state.data.type = 'bar';
        this.plot.load(this.state.data);
    };

    renderSwitchButtons = () => {
        let buttons = [
            {
                name: this.i18n.ru.pieChart,
                active: this.state.data.type === void 0,
                callback: this.renderPieChart
            },
            {
                name: this.i18n.ru.barChart,
                active: this.state.data.type === 'bar',
                callback: this.renderBarChart
            },
        ];
        // FIXME: Если всё время вызывать generate, то лучше перенести кнопки из графика...
        d3.select(this.id)
            .insert('div', ":first-child")
            .attr('class', 'btn-group pull-right')
            .attr('role', 'group')
            .attr('aria-label', 'Toggle')
            .selectAll('button')
            .data(buttons)
            .enter().append('button').attr('class', function (d) {
                if (d.active) {
                    return 'btn btn-default active';
                } else {
                    return 'btn btn-default';
                }
            })
            .text(d => d.name)
            .on('click',  (d, i) => {
                const buttons = d3.select(this.id)
                    .select('div')
                    .selectAll('button')
                    .classed('active', false);
                d3.select(buttons[0][i]).classed('active', true);
                d.callback();
            });
    };
}

export default ParticipantsYear;