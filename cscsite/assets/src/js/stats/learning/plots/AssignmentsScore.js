import * as d3 from "d3";
import * as c3 from "c3";
import $ from 'jquery';
import mix from '../../MixinBuilder';
import FilteredPlot from './FilteredPlot';
import AssignmentsFilterMixin from './AssignmentsFilterMixin';


class AssignmentsScore extends mix(FilteredPlot).with(AssignmentsFilterMixin) {
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
        super(id, options);
        this.id = id;
        this.type = 'bar';
        this.rawJSON = {};
        this.plot = undefined;
        this.templates = options.templates || {};

        this.state = {
            data: [],  // filtered data
            titles: undefined,  // assignment titles
        };

        let promise = options.apiRequest ||
                      this.constructor.getStats(options.course_session_id);
        promise
            // Memorize raw JSON data for future conversions
            .then((rawJSON) => { this.rawJSON = rawJSON; return rawJSON })
            .then(this.calculateFilterProps)
            .then(this.convertData)
            .done(this.render);
    }

    static getStats(course_session_id) {
        let dataURL = window.URLS["api:stats_assignments"](course_session_id);
        return $.getJSON(dataURL);
    }

    convertData = (rawJSON) => {
        let titles = [],
            rows = [[this.i18n.ru.lines.pass, this.i18n.ru.lines.mean,
                this.i18n.ru.lines.max]];

        rawJSON
            .filter((a) => this.matchFilters(a, "assignment"))
            .forEach((assignment) => {
                titles.push(assignment.title);
                let sum = 0,
                    cnt = 0;
                assignment.assigned_to
                    .filter((sa) => this.matchFilters(sa, "student_assignment"))
                    .forEach((student) => {
                        if (student.grade !== null) {
                            sum += student.grade;
                            cnt += 1;
                        }
                });
                let mean = (cnt === 0) ? 0 : (sum / cnt).toFixed(1);
                rows.push([assignment.grade_min, mean, assignment.grade_max]);
        });

        this.state.titles = titles;
        this.state.data = rows;
        return this.state.data;
    };

    render = (data) => {
        if (!this.state.titles.length) {
            $('#' + this.id).html(this.i18n.ru.no_assignments);
            return;
        }

        // Let's generate here, a lot of troubles with c3.load method right now
        console.log(data);
        this.plot = c3.generate({
            bindto: '#' + this.id,
            oninit: () => { this.renderFilters() },
            data: {
                type: this.type,
                order: null, // https://github.com/c3js/c3/issues/1945
                rows: data
            },
            tooltip: {
                format: {
                    title: (d) => this.state.titles[d],
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
                position: 'bottom'
            },
            grid: {
                y: {
                    show: true
                }
            },
        });
    };

    /**
     * Collect filter elements data which will be appended right after plot
     * with d3js. Each element must have `html` attribute. Callback is optional.
     * @returns {[*,*]}
     */
    getFilterFormData = () => {
        let self = this;
        let data = [
            // Filter by student gender
            {
                id: `#${this.id}-gender-filter`,
                html: this.templates.filters.gender({
                    filterId: `${this.id}-gender-filter`
                }),
                callback: function () {
                    $(this.id).selectpicker('render')
                        .on('changed.bs.select', function () {
                            self.filters.state["student.gender"] = this.value;
                        });
                }
            },
            // Filter by `is_online`
            {
                id: `#${this.id}-is-online-filter`,
                html: this.templates.filters.isOnline({
                    filterId: `${this.id}-is-online-filter`,
                }),
                callback: function () {
                    $(this.id).selectpicker('render')
                        .on('changed.bs.select', function () {
                            self.filters.state.is_online = (this.value === "") ?
                                undefined : (this.value === "true");
                        });
                }
            },
            // Filter by curriculum year
            this.filterDataCurriculumYear(),  // can return null
            // Submit button
            {
                isSubmitButton: true,
                html: this.templates.filters.submitButton()
            }
        ];
        return data.filter((e) => e);
    };

    submitButtonHandler = () => {
        let filteredData = this.convertData(this.rawJSON);
        this.plot.load({
            type: this.type,
            rows: filteredData,
            // Clean plot if no data, otherwise save animation transition
            // FIXME: убрать бы эту зависимость от state
            unload: this.state.titles.length > 0 ? {} : true
        });
        return false;
    };
}

export default AssignmentsScore;