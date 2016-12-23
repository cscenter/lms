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
        this.data = {};
        this.plot = undefined;
        this.templates = options.templates || {};

        let promise = options.apiRequest ||
                      this.getStats(options.course_session_id);
        promise
            .then(this.convertData)
            .done(this.render)
            .done(this.renderFilters);
    }

    static getStats(course_session_id) {
        let dataURL = URLS["api:stats_assignments"](course_session_id);
        return $.getJSON(dataURL);
    }

    convertData = (jsonData) => {
        let titles = [],
            participants = [this.i18n.ru.participants],
            passed = [this.i18n.ru.passed];
        jsonData.forEach(function (assignment) {
            let _passed = 0,
                _participants = 0,
                assignments = assignment.assigned_to;
            assignments.forEach(function(student) {
               _participants += 1;
               _passed += student.sent;
            });
            titles.push(assignment.title);
            participants.push(_participants);
            passed.push(_passed);
        });

        this.data = [titles, participants, passed];
        console.debug(this.data);
        return this.data;
    };

    renderFilters = () => {
        console.log("FILTERS. TEMP");
        console.log(this.templates.filters.gender({filterId: "test"}));
        let formData = [
            {

            }
        ];
        // get .col-xs-10 node
        let plotWrapperNode = d3.select(this.id).node().parentNode,
            // first, skip #text node between .col-xs-10 and .col-xs-2
            filterWrapperNode = plotWrapperNode.nextSibling.nextSibling;
        d3.select(filterWrapperNode)
            .selectAll('div.form-group')
            .data(formData)
            .enter()
            .append('div')
            .attr('class', 'form-group')
            .text( (d) => "This is a text for " + d);
    };

    render = (data) => {
        // TODO: если нет заданий - не рисовать график

        let titles = data[0],
            columns = data.slice(1);

        if (!titles.length) {
            $(this.id).html(this.i18n.ru.no_assignments);
            return;
        }

        // Let's generate here, a lot of troubles with c3.load method right now
        console.log(columns);
        this.plot = c3.generate({
            bindto: this.id,
            data: {
                type: this.type,
                columns: columns
            },
            // legend: {
            //     position: 'right'
            // },
            tooltip: {
                format: {
                    title: function (d) { return titles[d].slice(0, 80); },
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