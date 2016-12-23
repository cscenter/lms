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
        this.state = {
            data: [],  // filtered data
            titles: undefined,  // assignment titles
            filters: {
                gender: undefined,
                curriculumYear: {
                    value: undefined,
                    choices: undefined
                }
            }
        };
        this.plot = undefined;
        this.templates = options.templates || {};

        let promise = options.apiRequest ||
                      this.getStats(options.course_session_id);
        promise
            // Memorize raw JSON data for future conversions
            .then((rawJSON) => { this.rawJSON = rawJSON; return rawJSON })
            .then(this.preCalculateState)
            .then(this.convertData)
            .done(this.render)
            .done(this.renderFilters);
    }

    static getStats(course_session_id) {
        let dataURL = URLS["api:stats_assignments"](course_session_id);
        return $.getJSON(dataURL);
    }

    // Memorize assignments titles and collect filter values
    // We don't want to calculate this data every time on filter event
    preCalculateState = (rawJSON) => {
        let titles = [],
            curriculumYearChoices = new Set();
        rawJSON.forEach(function (assignment) {
            titles.push(assignment.title);
            assignment.assigned_to.forEach(function(sa) {
                curriculumYearChoices.add(sa.student.curriculum_year);
            });
        });
        this.state.titles = titles;
        this.state.filters.curriculumYear.choices = curriculumYearChoices;
        return rawJSON;
    };

    matchFilter = ([value, stateAttrName]) => {
        let stateAttr = this.state.filters[stateAttrName],
            // stateAttr can be a value or Object with `value` attribute
            stateValue = (stateAttr === Object(stateAttr)) ? stateAttr.value : stateAttr;
        return stateValue == undefined || stateValue == ""
               || stateValue == value;
    };

    // Recalculate data based on current filters state
    convertData = (rawJSON) => {
        let participants = [this.i18n.ru.participants],
            passed = [this.i18n.ru.passed];
        rawJSON.forEach((assignment) => {
            let _passed = 0,
                _participants = 0;
            assignment.assigned_to.forEach((sa) => {
                // Array of [dataValue, stateAttrName]
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
        });

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
                    self.state.filters.curriculumYear.value = this.value;
                });
            }
        };
    };

    getFilterData = () => {
        let data = [this.genderFilter()];
        if (this.state.filters.curriculumYear.choices.size > 0) {
            data.push(this.curriculumYearFilter(
                [...this.state.filters.curriculumYear.choices]));
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
            // first, skip #text node between .col-xs-10 and .col-xs-2
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
            .filter(function(d) { return d.isSubmitButton === true })
            .on("click", () => {
                let filteredData = this.convertData(this.rawJSON);
                this.plot.load({
                    type: this.type,
                    columns: filteredData
                });
                return false;
            })
    };

    render = (data) => {
        console.log('STATE', this.state);
        if (!this.state.titles.length) {
            $('#' + this.id).html(this.i18n.ru.no_assignments);
            return;
        }

        let titles = this.state.titles;

        // Let's generate here, a lot of troubles with c3.load method right now
        console.log(data);
        this.plot = c3.generate({
            bindto: '#' + this.id,
            data: {
                type: this.type,
                columns: data
            },
            tooltip: {
                format: {
                    title: function (d) {
                        return titles[d].slice(0, 80);
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