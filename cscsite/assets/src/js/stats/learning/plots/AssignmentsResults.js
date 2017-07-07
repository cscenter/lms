import * as d3 from "d3";
import * as c3 from "c3";
import $ from 'jquery';
import mix from '../../MixinBuilder';
import FilteredPlot from './FilteredPlot';
import AssignmentsFilterMixin from './AssignmentsFilterMixin';

class AssignmentsResults extends mix(FilteredPlot).with(AssignmentsFilterMixin) {
    i18n = {
        lang: 'ru',
        ru: {
            no_assignments: "Заданий не найдено.",
            // TODO: Load from backend?
            grades: {
                not_submitted: "Не отправлено",
                not_checked: "Не проверено",
                unsatisfactory: "Незачет",
                pass: "Удовлетворительно",
                good: "Хорошо",
                excellent: "Отлично"
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

        // Order is unspecified for Object, but I believe browsers sort
        // it in a proper way
        // TODO: rename?
        this.states = Object.keys(this.i18n.ru.grades).reduce((m, k) => {
            return m.set(k, this.i18n.ru.grades[k]);
        }, new Map());

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
        let states = Array.from(this.states, ([k, v]) => v),
            titles = [],
            rows = [states];

        rawJSON
            .filter((a) => this.matchFilters(a, "assignment"))
            .forEach((assignment) => {
                titles.push(assignment.title);
                let counters = states.reduce(function (a, b) {
                        return a.set(b, 0);
                    }, new Map());
                assignment.assigned_to
                    .filter((sa) => this.matchFilters(sa, "student_assignment"))
                    .forEach((student) => {
                        let state = this.states.get(student.state);
                        counters.set(state, counters.get(state) + 1);
                });
                rows.push(Array.from(counters, ([k, v]) => v));
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
                rows: data,
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
            grid: {
                y: {
                    show: true
                }
            },
            color: {
                pattern: ['#7f7f7f', '#ffbb78', '#d62728', '#ff7f0e',  '#2ca02c', '#9c27b0',   '#c7c7c7', '#bcbd22', '#dbdb8d', '#17becf', '#9edae5']
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
            this.filterByStudentGroup(),
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

export default AssignmentsResults;