import * as d3 from "d3";
import mix from '../MixinBuilder';
import FilteredPlot from './FilteredPlot';
import AssignmentsFilterMixin from './AssignmentsFilterMixin';
// FIXME: remove moment.js?
import * as moment from 'moment';
// TODO: Also, used global c3, URLS, jQuery, moment.js. Investigate how to import them explicitly

class AssignmentsDeadline extends mix(FilteredPlot).with(AssignmentsFilterMixin) {
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
                // no_submission: "Не сдавал"
            }
        }
    };

    constructor(id, options) {
        super(id, options);
        // Remove
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
        this.types = Object.keys(this.i18n.ru.types).reduce((m, k) => {
            return m.set(k, this.i18n.ru.types[k]);
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
        let dataURL = URLS["api:stats_assignments"](course_session_id);
        return $.getJSON(dataURL);
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
                    return this.types.get("lte3to24hours");
                } else {
                    return this.types.get("lt3hours");
                }
            }
        }
    }

    convertData = (jsonData) => {
        let types = Array.from(this.types.values()),
            titles = [],
            rows = [types];
        jsonData
            .filter((a) => a.is_online !== false)
            .forEach((assignment) => {
                titles.push(assignment.title);
                let deadline = new Date(assignment.deadline_at);
                let counters = types.reduce(function (a, b) {
                        return a.set(b, 0);
                    }, new Map());
                assignment.assigned_to
                    .filter((s) => this.matchFilters(s, "student_assignment"))
                    .forEach((student) => {
                        let type = this.toType(deadline, student.first_submission_at);
                        if (type !== undefined) {
                            counters.set(type, counters.get(type) + 1);
                        } else {
                            // console.debug("Unknown deadline type for: ", student);
                        }
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
        this.plot = c3.generate({
            bindto: '#' + this.id,
            oninit: () => { this.renderFilters() },
            data: {
                type: this.type,
                rows: data,
                groups: [
                    Array.from(this.types, ([k, v]) => v)
                ]
            },
            tooltip: {
                format: {
                    title: (d) => { return this.state.titles[d] },
                }
            },
            axis: {
                x: {
                    tick: {
                      format: function (x) { return ""; }
                    }
                }
            },
            color: {
                pattern: ['#d62728', '#9c27b0', '#ff7f0e', '#ffbb78', '#2ca02c', '#9467bd', '#c5b0d5', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d', '#17becf', '#9edae5']
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
        // FIXME: попробовать убрать Array.from везде. Но надо искать баг в самой c3.js
        // this.plot.groups([Array.from(this.types, ([k, v]) => v)]);
        return false;
    };
}

export default AssignmentsDeadline;