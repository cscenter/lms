import * as d3 from "d3";
// TODO: Also, used global c3, URLS, jQuery. Investigate how to import them explicitly

class AssignmentsProgress {
    // FIXME: изучить как лучше передавать перевод. Кажется, что это должен быть отдельный сервис
    i18n = {
        lang: 'ru',
        ru: {
            titles: "Задания",
            participants: "Слушатели курса",
            passed: "Сдали задание",
            no_assignments: "Заданий не найдено."
        }
    };

    constructor(id, options) {
        this.id = id;
        this.type = 'line';
        this.rawJSON = {};
        this.props = {
            choices: {
                curriculumYear: undefined
            }
        };
        this.state = {
            data: [],  // filtered data
            titles: undefined,  // assignment titles
            filters: {
                gender: undefined,
                isOnline: undefined,
                curriculumYear: undefined
            }
        };
        this.plot = undefined;
        this.templates = options.templates || {};

        let promise = options.apiRequest ||
                      this.getStats(options.course_session_id);
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

    /**
     * Collect filter choices. Don't want to calculate this data every
     * time on filter event
     * @param rawJSON
     * @returns {*}
     */
    calculateFilterProps = (rawJSON) => {
        let curriculumYearChoices = new Set();
        rawJSON.forEach(function (assignment) {
            assignment.assigned_to.forEach(function(sa) {
                curriculumYearChoices.add(sa.student.curriculum_year);
            });
        });
        this.props.choices.curriculumYear = curriculumYearChoices;
        return rawJSON;
    };

    matchFilter = ([value, stateAttrName]) => {
        let stateValue = this.state.filters[stateAttrName];
        return stateValue === undefined || stateValue === ""
               || stateValue === value;
    };

    // Recalculate data based on current filters state
    convertData = (rawJSON) => {
        let participants = [this.i18n.ru.participants],
            passed = [this.i18n.ru.passed],
            titles = [];
        rawJSON.forEach((assignment) => {
            if (this.matchFilter([assignment.is_online, "isOnline"])) {
                titles.push(assignment.title);
                let _passed = 0,
                    _participants = 0;
                assignment.assigned_to.forEach((sa) => {
                    // Array of [dataValue, stateAttrName]
                    // FIXME: надо куда-то перенести эти фильтры в настройки, чтобы не городить такой огород
                    let filterPairs = [
                        [sa.student.gender, "gender"],
                        [sa.student.curriculum_year, "curriculumYear"],
                    ];
                    if (filterPairs.every(this.matchFilter)) {
                       _participants += 1;
                       _passed += sa.sent;
                    }
                });
                participants.push(_participants);
                passed.push(_passed);
            }
        });
        this.state.titles = titles;
        this.state.data = [participants, passed];
        return this.state.data;
    };

    genderFilter = () => {
        let self = this,
            filterId = this.id +  "-gender-filter";
        return {
            id: '#' + filterId,
            html: this.templates.filters.gender({
                filterId: filterId
            }),
            callback: function() {
                $(this.id).selectpicker('render')
                .on('changed.bs.select', function () {
                    self.state.filters.gender = this.value;
                });
            }
        };
    };

    isOnlineFilter = () => {
        let self = this,
            filterId = this.id +  "-is-online-filter";
        return {
            id: '#' + filterId,
            html: this.templates.filters.isOnline({
                filterId: filterId
            }),
            callback: function() {
                $(this.id).selectpicker('render')
                .on('changed.bs.select', function () {
                    self.state.filters.isOnline = (this.value === "") ?
                        undefined : (this.value === "true");
                });
            }
        };
    };

    curriculumYearFilter = (choices) => {
        let self = this,
            filterId = this.id +  "-curriculum-year-filter";
        return {
            id: '#' + filterId,
            html: this.templates.filters.curriculumYear({
                filterId: filterId,
                items: choices
            }),
            callback: function() {
                $(this.id).selectpicker('render')
                .on('changed.bs.select', function () {
                    self.state.filters.curriculumYear =
                        (this.value !== "") ? parseInt(this.value) : this.value;
                });
            }
        };
    };

    /**
     * Collect for d3js filter elements data which will be appended right after
     * plot. Each element must have `html` attribute and callback if necessary.
     * @returns {[*,*]}
     */
    getFilterData = () => {
        let data = [
            this.genderFilter(),
            this.isOnlineFilter()
        ];
        if (this.props.choices.curriculumYear.size > 0) {
            data.push(this.curriculumYearFilter(
                [...this.props.choices.curriculumYear].sort()));
        }
        data.push({
            isSubmitButton: true,
            html: this.templates.filters.submitButton()
        });
        return data;
    };

    renderFilters = () => {
        // get .col-xs-10 node
        let plotWrapperNode = d3.select('#' + this.id).node().parentNode,
            // first `nextSibling` for skipping #text node between .col-xs-10
            // and .col-xs-2
            filterWrapperNode = plotWrapperNode.nextSibling.nextSibling;
        d3.select(filterWrapperNode)
            .selectAll('div.form-group')
            .data(this.getFilterData())
            .enter()
            .append('div')
            .attr('class', 'form-group')
            .html( (d) => d.html)
            .each( (d) => {
                if (d.callback !== undefined) {
                    d.callback();
                }
            })
            // On last step, append filter button
            .filter(function(d) { return d.isSubmitButton === true })
            .on("click", () => {
                let filteredData = this.convertData(this.rawJSON);
                this.plot.load({
                    type: this.type,
                    columns: filteredData,
                    // Clean plot if no data, otherwise save transition
                    unload: this.state.titles.length > 0 ? {} : true
                });
                return false;
            })
    };

    render = (data) => {
        if (!this.state.titles.length) {
            $('#' + this.id).html(this.i18n.ru.no_assignments);
            return;
        }

        this.plot = c3.generate({
            bindto: '#' + this.id,
            oninit: () => { this.renderFilters() },
            data: {
                type: this.type,
                columns: data
            },
            tooltip: {
                format: {
                    title: (d) => {
                        if (this.state.titles[d] !== void 0) {
                            return this.state.titles[d].slice(0, 80);
                        } else {
                            return "";
                        }
                    },
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
            }
        });
    };
}

export default AssignmentsProgress;