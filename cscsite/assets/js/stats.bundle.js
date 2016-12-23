/******/ (function(modules) { // webpackBootstrap
/******/ 	// The module cache
/******/ 	var installedModules = {};

/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {

/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId])
/******/ 			return installedModules[moduleId].exports;

/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			exports: {},
/******/ 			id: moduleId,
/******/ 			loaded: false
/******/ 		};

/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);

/******/ 		// Flag the module as loaded
/******/ 		module.loaded = true;

/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}


/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;

/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;

/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "/static/";

/******/ 	// Load entry module and return exports
/******/ 	return __webpack_require__(0);
/******/ })
/************************************************************************/
/******/ ([
/* 0 */
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function($) {'use strict';

	var _ParticipantsYear = __webpack_require__(2);

	var _ParticipantsYear2 = _interopRequireDefault(_ParticipantsYear);

	var _ParticipantsGroup = __webpack_require__(5);

	var _ParticipantsGroup2 = _interopRequireDefault(_ParticipantsGroup);

	var _AssignmentsProgress = __webpack_require__(6);

	var _AssignmentsProgress2 = _interopRequireDefault(_AssignmentsProgress);

	var _AssignmentsDeadline = __webpack_require__(7);

	var _AssignmentsDeadline2 = _interopRequireDefault(_AssignmentsDeadline);

	var _AssignmentsResults = __webpack_require__(10);

	var _AssignmentsResults2 = _interopRequireDefault(_AssignmentsResults);

	var _AssignmentsScore = __webpack_require__(11);

	var _AssignmentsScore2 = _interopRequireDefault(_AssignmentsScore);

	var _EnrollmentsResults = __webpack_require__(12);

	var _EnrollmentsResults2 = _interopRequireDefault(_EnrollmentsResults);

	function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

	var template = __webpack_require__(13);

	// Filter DOM elements here
	var termFilter = $('#term-filter'),
	    courseFilter = $('#course-filter'),
	    courseFilterForm = $('#courses-filter-form');

	var fn = {
	    init: function init() {
	        var courseSessionId = json_data.course_session_id;
	        fn.renderPlots(courseSessionId);
	        fn.initCoursesFilter();
	    },

	    renderPlots: function renderPlots(courseSessionId) {
	        // Prepare templates
	        var filterGenderTpl = template(document.getElementById("plot-filter-gender-template").innerHTML),
	            filterCurriculumYearTpl = template(document.getElementById("plot-filter-curriculum_year-template").innerHTML),
	            filterSubmitButtonTpl = template(document.getElementById("plot-filter-submit-button").innerHTML);
	        // Participants
	        var options = {
	            course_session_id: courseSessionId,
	            apiRequest: _ParticipantsYear2.default.getStats(courseSessionId)
	        };
	        new _ParticipantsYear2.default('#plot-participants-by-year', options);
	        new _ParticipantsGroup2.default('#plot-participants-by-group', options);
	        // Assignments
	        options = {
	            course_session_id: courseSessionId,
	            templates: {
	                filters: {
	                    gender: filterGenderTpl,
	                    curriculumYear: filterCurriculumYearTpl,
	                    submitButton: filterSubmitButtonTpl
	                }
	            },
	            apiRequest: _AssignmentsProgress2.default.getStats(courseSessionId)
	        };
	        new _AssignmentsProgress2.default('plot-assignments-progress', options);
	        new _AssignmentsDeadline2.default('#plot-assignments-deadline', options);
	        new _AssignmentsResults2.default('#plot-assignments-results', options);
	        new _AssignmentsScore2.default('#plot-assignments-score', options);
	        // Enrollments
	        new _EnrollmentsResults2.default('#plot-enrollments-results', courseSessionId);
	    },

	    initCoursesFilter: function initCoursesFilter() {
	        courseFilter.on('change', function () {
	            $('button[type=submit]', courseFilterForm).removeAttr('disabled');
	        });
	        // TODO: refactor
	        termFilter.on('change', function () {
	            var term_id = $(this).val();
	            var courses = json_data.courses[term_id];
	            courseFilter.empty();
	            courses.forEach(function (co) {
	                var opt = document.createElement('option');
	                opt.value = co['pk'];
	                opt.innerHTML = co['course__name'];
	                courseFilter.get(0).appendChild(opt);
	            });
	            courseFilter.selectpicker('refresh');
	            $('button[type=submit]', courseFilterForm).removeAttr('disabled');
	        });
	    }
	};

	$(document).ready(function () {
	    fn.init();
	});
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(1)))

/***/ },
/* 1 */
/***/ function(module, exports) {

	module.exports = jQuery;

/***/ },
/* 2 */
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function(c3, $) {"use strict";

	exports.__esModule = true;

	var _d = __webpack_require__(4);

	var d3 = _interopRequireWildcard(_d);

	function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

	function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

	// TODO: Also, used global c3, URLS, jQuery. Investigate how to import them explicitly

	var ParticipantsYear = function () {
	    function ParticipantsYear(id, options) {
	        var _this = this;

	        _classCallCheck(this, ParticipantsYear);

	        this.i18n = {
	            ru: {
	                diagram: "Диаграмма",
	                plot: "График",
	                students: ""
	            }
	        };

	        this.convertData = function (jsonData) {
	            var data = {};
	            jsonData.forEach(function (e) {
	                if (!(e.curriculum_year in data)) {
	                    data[e.curriculum_year] = 0;
	                }
	                data[e.curriculum_year] += 1;
	            });
	            _this.data = data;
	            // FIXME: по-моему я это уже не юзаю!
	            var columns = [];
	            for (var key in data) {
	                columns.push([key, data[key]]);
	            }
	            return columns;
	        };

	        this.renderPieChart = function () {
	            _this.type = 'pie';
	            _this.plot.load({
	                type: _this.type,
	                columns: _this.dataForPie(),
	                unload: true
	            });
	        };

	        this.renderBarChart = function () {
	            if (_this.type == 'bar') {
	                return;
	            }
	            _this.type = 'bar';
	            _this.plot.load({
	                type: _this.type,
	                xs: { 'students': 'year' },
	                xFormat: '%Y',
	                x: 'year',
	                columns: _this.dataForLine(),
	                names: {
	                    students: _this.i18n.ru.students
	                },
	                unload: true
	            });
	            _this.plot.legend.hide();
	        };

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
	                    value: function value(_value, ratio, id) {
	                        if (_this.type == 'pie') {
	                            return _value + '&nbsp;чел.';
	                        } else {
	                            return _value;
	                        }
	                    }
	                }
	            },
	            data: {
	                type: this.type,
	                columns: []
	            }
	        });
	        // Switch plot type button
	        var buttons = [{ name: this.i18n.ru.diagram, callback: this.renderPieChart }, { name: this.i18n.ru.plot, callback: this.renderBarChart }];
	        // FIXME: Если всё время вызывать generate, то лучше перенести кнопки из графика...
	        d3.select(this.id).insert('div', ":first-child").attr('class', 'btn-group pull-right').attr('role', 'group').attr('aria-label', 'Toggle').selectAll('button').data(buttons).enter().append('button').attr('class', 'btn btn-default').attr('data-id', function (id) {
	            return id;
	        }).text(function (d) {
	            return d.name;
	        }).on('click', function (d) {
	            d.callback();
	        });

	        var promise = options.apiRequest || this.getStats(options.course_session_id);
	        promise.then(this.convertData).done(this.renderPieChart);
	    }

	    ParticipantsYear.getStats = function getStats(course_session_id) {
	        var dataURL = URLS["api:stats_participants"](course_session_id);
	        return $.getJSON(dataURL);
	    };

	    ParticipantsYear.prototype.dataForPie = function dataForPie() {
	        var columns = [];
	        for (var key in this.data) {
	            columns.push([key, this.data[key]]);
	        }
	        return columns;
	    };

	    ParticipantsYear.prototype.dataForLine = function dataForLine() {
	        var x = ['year'],
	            y = ['students'];
	        for (var key in this.data) {
	            x.push(key);
	            y.push(this.data[key]);
	        }
	        return [x, y];
	    };

	    ParticipantsYear.prototype.loadData = function loadData(columns) {};

	    return ParticipantsYear;
	}();

	exports.default = ParticipantsYear;
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(3), __webpack_require__(1)))

/***/ },
/* 3 */
/***/ function(module, exports) {

	module.exports = c3;

/***/ },
/* 4 */
/***/ function(module, exports) {

	module.exports = d3;

/***/ },
/* 5 */
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function(c3, $) {"use strict";

	exports.__esModule = true;

	var _d = __webpack_require__(4);

	var d3 = _interopRequireWildcard(_d);

	function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

	function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

	// TODO: Also, used global c3, URLS, jQuery. Investigate how to import them explicitly

	var ParticipantsGroup = function () {
	    function ParticipantsGroup(id, options) {
	        var _this = this;

	        _classCallCheck(this, ParticipantsGroup);

	        this.i18n = {
	            ru: {
	                groups: {
	                    STUDENT_CENTER: "Студент центра",
	                    VOLUNTEER: "Вольнослушатель",
	                    GRADUATE: "Выпускник"
	                },
	                total_participants: "Всего слушателей курса"
	            }
	        };

	        this.appendParticipantsInfo = function () {
	            var total = Object.values(_this.data).reduce(function (a, b) {
	                return a + b;
	            }, 0);

	            d3.select(_this.id).insert('div', ":first-child").attr('class', 'info').selectAll('div').data([total]).enter().append('div').text(function (d) {
	                return _this.i18n.ru.total_participants + ': ' + d;
	            });
	        };

	        this.convertData = function (jsonData) {
	            var data = Object.keys(_this.groups).reduce(function (a, b) {
	                a[b] = 0;return a;
	            }, {});
	            // Inaccuracy if student have student and volunteer group or haven't both.
	            jsonData.forEach(function (student) {
	                student.groups.forEach(function (group) {
	                    if (group in data) {
	                        data[group] += 1;
	                    }
	                });
	            });
	            _this.data = data;
	            // Prepare data for plot
	            var columns = [];
	            for (var key in data) {
	                if (key != 3 || data[key] != 0) {
	                    columns.push([_this.groups[key], data[key]]);
	                }
	            }
	            console.log(columns);
	            return columns;
	        };

	        this.render = function (columns) {
	            _this.plot.load({
	                type: _this.type,
	                columns: columns
	            });
	        };

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
	                    value: function value(_value, ratio, id) {
	                        return _value + '&nbsp;чел.';
	                    }
	                }
	            },
	            data: {
	                type: this.type,
	                columns: []
	            }
	        });
	        var promise = options.apiRequest || this.getStats(options.course_session_id);
	        promise.then(this.convertData).then(this.render).done(this.appendParticipantsInfo);
	    }

	    ParticipantsGroup.getStats = function getStats(course_session_id) {
	        var dataURL = URLS["api:stats_participants"](course_session_id);
	        return $.getJSON(dataURL);
	    };

	    return ParticipantsGroup;
	}();

	exports.default = ParticipantsGroup;
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(3), __webpack_require__(1)))

/***/ },
/* 6 */
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function($, c3) {"use strict";

	exports.__esModule = true;

	var _d = __webpack_require__(4);

	var d3 = _interopRequireWildcard(_d);

	function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

	function _toConsumableArray(arr) { if (Array.isArray(arr)) { for (var i = 0, arr2 = Array(arr.length); i < arr.length; i++) { arr2[i] = arr[i]; } return arr2; } else { return Array.from(arr); } }

	function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

	// TODO: Also, used global c3, URLS, jQuery. Investigate how to import them explicitly

	var AssignmentsProgress = function () {
	    function AssignmentsProgress(id, options) {
	        var _this = this;

	        _classCallCheck(this, AssignmentsProgress);

	        this.i18n = {
	            lang: 'ru',
	            ru: {
	                titles: "Задания",
	                participants: "Слушатели курса",
	                passed: "Сдали задание",
	                no_assignments: "Заданий не найдено."
	            }
	        };

	        this.preCalculateState = function (rawJSON) {
	            var titles = [],
	                curriculumYearChoices = new Set();
	            rawJSON.forEach(function (assignment) {
	                titles.push(assignment.title);
	                assignment.assigned_to.forEach(function (sa) {
	                    curriculumYearChoices.add(sa.student.curriculum_year);
	                });
	            });
	            _this.state.titles = titles;
	            _this.state.filters.curriculumYear.choices = curriculumYearChoices;
	            return rawJSON;
	        };

	        this.matchFilter = function (_ref) {
	            var value = _ref[0],
	                stateAttrName = _ref[1];

	            var stateAttr = _this.state.filters[stateAttrName],

	            // stateAttr can be a value or Object with `value` attribute
	            stateValue = stateAttr === Object(stateAttr) ? stateAttr.value : stateAttr;
	            return stateValue == undefined || stateValue == "" || stateValue == value;
	        };

	        this.convertData = function (rawJSON) {
	            var participants = [_this.i18n.ru.participants],
	                passed = [_this.i18n.ru.passed];
	            rawJSON.forEach(function (assignment) {
	                var _passed = 0,
	                    _participants = 0;
	                assignment.assigned_to.forEach(function (sa) {
	                    // Array of [dataValue, stateAttrName]
	                    var filterPairs = [[sa.student.gender, "gender"], [sa.student.curriculum_year, "curriculumYear"]];
	                    if (filterPairs.every(_this.matchFilter)) {
	                        _participants += 1;
	                        _passed += sa.sent;
	                    }
	                });
	                participants.push(_participants);
	                passed.push(_passed);
	            });

	            _this.state.data = [participants, passed];
	            return _this.state.data;
	        };

	        this.genderFilter = function () {
	            var self = _this,
	                filterId = _this.id + "-gender-filter";
	            return {
	                id: '#' + filterId,
	                html: _this.templates.filters.gender({
	                    filterId: filterId
	                }),
	                callback: function callback() {
	                    $(this.id).selectpicker('render').on('changed.bs.select', function () {
	                        self.state.filters.gender = this.value;
	                    });
	                }
	            };
	        };

	        this.curriculumYearFilter = function (choices) {
	            var self = _this,
	                filterId = _this.id + "-curriculum-year-filter";
	            return {
	                id: '#' + filterId,
	                html: _this.templates.filters.curriculumYear({
	                    filterId: filterId,
	                    items: choices
	                }),
	                callback: function callback() {
	                    $(this.id).selectpicker('render').on('changed.bs.select', function () {
	                        self.state.filters.curriculumYear.value = this.value;
	                    });
	                }
	            };
	        };

	        this.getFilterData = function () {
	            var data = [_this.genderFilter()];
	            if (_this.state.filters.curriculumYear.choices.size > 0) {
	                data.push(_this.curriculumYearFilter([].concat(_toConsumableArray(_this.state.filters.curriculumYear.choices))));
	            }
	            data.push({
	                isSubmitButton: true,
	                html: _this.templates.filters.submitButton()
	            });
	            return data;
	        };

	        this.renderFilters = function () {
	            // get .col-xs-10 node
	            var plotWrapperNode = d3.select('#' + _this.id).node().parentNode,

	            // first, skip #text node between .col-xs-10 and .col-xs-2
	            filterWrapperNode = plotWrapperNode.nextSibling.nextSibling;
	            d3.select(filterWrapperNode).selectAll('div.form-group').data(_this.getFilterData()).enter().append('div').attr('class', 'form-group').html(function (d) {
	                return d.html;
	            }).each(function (d) {
	                if (d.callback !== undefined) {
	                    d.callback();
	                }
	            }).filter(function (d) {
	                return d.isSubmitButton === true;
	            }).on("click", function () {
	                var filteredData = _this.convertData(_this.rawJSON);
	                _this.plot.load({
	                    type: _this.type,
	                    columns: filteredData
	                });
	                return false;
	            });
	        };

	        this.render = function (data) {
	            console.log('STATE', _this.state);
	            if (!_this.state.titles.length) {
	                $('#' + _this.id).html(_this.i18n.ru.no_assignments);
	                return;
	            }

	            var titles = _this.state.titles;

	            // Let's generate here, a lot of troubles with c3.load method right now
	            console.log(data);
	            _this.plot = c3.generate({
	                bindto: '#' + _this.id,
	                data: {
	                    type: _this.type,
	                    columns: data
	                },
	                tooltip: {
	                    format: {
	                        title: function title(d) {
	                            return titles[d].slice(0, 80);
	                        }
	                    }
	                },
	                axis: {
	                    x: {
	                        tick: {
	                            format: function format(x) {
	                                return x + 1;
	                            }
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

	        this.id = id;
	        this.type = 'line';
	        this.rawJSON = {};
	        this.state = {
	            data: [], // filtered data
	            titles: undefined, // assignment titles
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

	        var promise = options.apiRequest || this.getStats(options.course_session_id);
	        promise
	        // Memorize raw JSON data for future conversions
	        .then(function (rawJSON) {
	            _this.rawJSON = rawJSON;return rawJSON;
	        }).then(this.preCalculateState).then(this.convertData).done(this.render).done(this.renderFilters);
	    }
	    // FIXME: изучить как лучше передавать перевод. Кажется, что это должен быть отдельный сервис


	    AssignmentsProgress.getStats = function getStats(course_session_id) {
	        var dataURL = URLS["api:stats_assignments"](course_session_id);
	        return $.getJSON(dataURL);
	    };

	    // Memorize assignments titles and collect filter values
	    // We don't want to calculate this data every time on filter event


	    // Recalculate data based on current filters state


	    return AssignmentsProgress;
	}();

	exports.default = AssignmentsProgress;
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(1), __webpack_require__(3)))

/***/ },
/* 7 */
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function($, c3) {'use strict';

	exports.__esModule = true;

	var _d = __webpack_require__(4);

	var d3 = _interopRequireWildcard(_d);

	var _moment = __webpack_require__(8);

	var moment = _interopRequireWildcard(_moment);

	function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

	function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }
	// FIXME: remove moment.js?


	// TODO: Also, used global c3, URLS, jQuery, moment.js. Investigate how to import them explicitly

	var AssignmentsDeadline = function () {
	    function AssignmentsDeadline(id, options) {
	        var _this = this;

	        _classCallCheck(this, AssignmentsDeadline);

	        this.i18n = {
	            lang: 'ru',
	            ru: {
	                no_assignments: "Заданий не найдено.",
	                types: {
	                    after: "После дедлайна",
	                    lt3hours: "Менее 3 часов",
	                    lte3to24hours: "3-24 часа",
	                    lte1to6days: "1-6 дней",
	                    gte7days: "7 дней и более"
	                }
	            }
	        };

	        this.convertData = function (jsonData) {
	            console.log(jsonData);
	            var types = Array.from(_this.types.values()),
	                titles = [],
	                rows = [types];
	            jsonData.forEach(function (assignment) {
	                titles.push(assignment.title);
	                var deadline = new Date(assignment.deadline_at),
	                    counters = types.reduce(function (a, b) {
	                    return a.set(b, 0);
	                }, new Map());
	                assignment.assigned_to.forEach(function (student) {
	                    var type = _this.toType(deadline, student.first_submission_at);
	                    if (type !== undefined) {
	                        counters.set(type, counters.get(type) + 1);
	                    } else {
	                        // console.debug("Unknown deadline type for: ", student);
	                    }
	                });
	                rows.push(Array.from(counters, function (_ref) {
	                    var k = _ref[0],
	                        v = _ref[1];
	                    return v;
	                }));
	            });

	            _this.data = {
	                titles: titles,
	                rows: rows
	            };
	            console.debug(_this.data);
	            return _this.data;
	        };

	        this.render = function (data) {
	            if (!data.titles.length) {
	                $(_this.id).html(_this.i18n.ru.no_assignments);
	                return;
	            }

	            // Let's generate here, a lot of troubles with c3.load method right now
	            console.log(data);
	            _this.plot = c3.generate({
	                bindto: _this.id,
	                data: {
	                    type: _this.type,
	                    rows: data.rows,
	                    groups: [Array.from(_this.types, function (_ref2) {
	                        var k = _ref2[0],
	                            v = _ref2[1];
	                        return v;
	                    })]
	                },
	                tooltip: {
	                    format: {
	                        title: function title(d) {
	                            return data.titles[d];
	                        }
	                    }
	                },
	                axis: {
	                    x: {
	                        tick: {
	                            format: function format(x) {
	                                return "";
	                            }
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
	                }
	            });
	        };

	        this.id = id;
	        this.type = 'bar';
	        this.data = {};
	        this.plot = undefined;

	        // Order is unspecified for Object, but I believe browsers sort
	        // it in a proper way
	        this.types = Object.keys(this.i18n.ru.types).reduce(function (m, k) {
	            return m.set(k, _this.i18n.ru.types[k]);
	        }, new Map());

	        var promise = options.apiRequest || this.getStats(options.course_session_id);
	        promise.then(this.convertData).done(this.render);
	    }

	    AssignmentsDeadline.getStats = function getStats(course_session_id) {
	        var dataURL = URLS["api:stats_assignments"](course_session_id);
	        return $.getJSON(dataURL);
	    };

	    // Convert diff between first submission and deadline to plot column type


	    AssignmentsDeadline.prototype.toType = function toType(deadline_at, submitted_at) {
	        if (submitted_at === null) {
	            return this.types.get("no_submission");
	        }
	        var diff_ms = deadline_at - new Date(submitted_at);
	        if (diff_ms <= 0) {
	            return this.types.get("after");
	        } else {
	            var diff = new moment.duration(diff_ms),
	                inDays = diff.asDays();
	            if (inDays >= 7) {
	                return this.types.get("gte7days");
	            } else if (inDays >= 1) {
	                return this.types.get("lte1to6days");
	            } else {
	                var inHours = diff.asHours();
	                if (inHours >= 3) {
	                    return this.types.get("lte3to24hours");
	                } else {
	                    return this.types.get("lt3hours");
	                }
	            }
	        }
	    };

	    return AssignmentsDeadline;
	}();

	exports.default = AssignmentsDeadline;
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(1), __webpack_require__(3)))

/***/ },
/* 8 */
/***/ function(module, exports, __webpack_require__) {

	var __WEBPACK_AMD_DEFINE_FACTORY__, __WEBPACK_AMD_DEFINE_RESULT__;/* WEBPACK VAR INJECTION */(function(module) {"use strict";

	var _typeof = typeof Symbol === "function" && typeof Symbol.iterator === "symbol" ? function (obj) { return typeof obj; } : function (obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; };

	//! moment.js
	//! version : 2.13.0
	//! authors : Tim Wood, Iskren Chernev, Moment.js contributors
	//! license : MIT
	//! momentjs.com
	!function (a, b) {
	  "object" == ( false ? "undefined" : _typeof(exports)) && "undefined" != typeof module ? module.exports = b() :  true ? !(__WEBPACK_AMD_DEFINE_FACTORY__ = (b), __WEBPACK_AMD_DEFINE_RESULT__ = (typeof __WEBPACK_AMD_DEFINE_FACTORY__ === 'function' ? (__WEBPACK_AMD_DEFINE_FACTORY__.call(exports, __webpack_require__, exports, module)) : __WEBPACK_AMD_DEFINE_FACTORY__), __WEBPACK_AMD_DEFINE_RESULT__ !== undefined && (module.exports = __WEBPACK_AMD_DEFINE_RESULT__)) : a.moment = b();
	}(undefined, function () {
	  "use strict";
	  function a() {
	    return fd.apply(null, arguments);
	  }function b(a) {
	    fd = a;
	  }function c(a) {
	    return a instanceof Array || "[object Array]" === Object.prototype.toString.call(a);
	  }function d(a) {
	    return a instanceof Date || "[object Date]" === Object.prototype.toString.call(a);
	  }function e(a, b) {
	    var c,
	        d = [];for (c = 0; c < a.length; ++c) {
	      d.push(b(a[c], c));
	    }return d;
	  }function f(a, b) {
	    return Object.prototype.hasOwnProperty.call(a, b);
	  }function g(a, b) {
	    for (var c in b) {
	      f(b, c) && (a[c] = b[c]);
	    }return f(b, "toString") && (a.toString = b.toString), f(b, "valueOf") && (a.valueOf = b.valueOf), a;
	  }function h(a, b, c, d) {
	    return Ja(a, b, c, d, !0).utc();
	  }function i() {
	    return { empty: !1, unusedTokens: [], unusedInput: [], overflow: -2, charsLeftOver: 0, nullInput: !1, invalidMonth: null, invalidFormat: !1, userInvalidated: !1, iso: !1, parsedDateParts: [], meridiem: null };
	  }function j(a) {
	    return null == a._pf && (a._pf = i()), a._pf;
	  }function k(a) {
	    if (null == a._isValid) {
	      var b = j(a),
	          c = gd.call(b.parsedDateParts, function (a) {
	        return null != a;
	      });a._isValid = !isNaN(a._d.getTime()) && b.overflow < 0 && !b.empty && !b.invalidMonth && !b.invalidWeekday && !b.nullInput && !b.invalidFormat && !b.userInvalidated && (!b.meridiem || b.meridiem && c), a._strict && (a._isValid = a._isValid && 0 === b.charsLeftOver && 0 === b.unusedTokens.length && void 0 === b.bigHour);
	    }return a._isValid;
	  }function l(a) {
	    var b = h(NaN);return null != a ? g(j(b), a) : j(b).userInvalidated = !0, b;
	  }function m(a) {
	    return void 0 === a;
	  }function n(a, b) {
	    var c, d, e;if (m(b._isAMomentObject) || (a._isAMomentObject = b._isAMomentObject), m(b._i) || (a._i = b._i), m(b._f) || (a._f = b._f), m(b._l) || (a._l = b._l), m(b._strict) || (a._strict = b._strict), m(b._tzm) || (a._tzm = b._tzm), m(b._isUTC) || (a._isUTC = b._isUTC), m(b._offset) || (a._offset = b._offset), m(b._pf) || (a._pf = j(b)), m(b._locale) || (a._locale = b._locale), hd.length > 0) for (c in hd) {
	      d = hd[c], e = b[d], m(e) || (a[d] = e);
	    }return a;
	  }function o(b) {
	    n(this, b), this._d = new Date(null != b._d ? b._d.getTime() : NaN), id === !1 && (id = !0, a.updateOffset(this), id = !1);
	  }function p(a) {
	    return a instanceof o || null != a && null != a._isAMomentObject;
	  }function q(a) {
	    return 0 > a ? Math.ceil(a) : Math.floor(a);
	  }function r(a) {
	    var b = +a,
	        c = 0;return 0 !== b && isFinite(b) && (c = q(b)), c;
	  }function s(a, b, c) {
	    var d,
	        e = Math.min(a.length, b.length),
	        f = Math.abs(a.length - b.length),
	        g = 0;for (d = 0; e > d; d++) {
	      (c && a[d] !== b[d] || !c && r(a[d]) !== r(b[d])) && g++;
	    }return g + f;
	  }function t(b) {
	    a.suppressDeprecationWarnings === !1 && "undefined" != typeof console && console.warn && console.warn("Deprecation warning: " + b);
	  }function u(b, c) {
	    var d = !0;return g(function () {
	      return null != a.deprecationHandler && a.deprecationHandler(null, b), d && (t(b + "\nArguments: " + Array.prototype.slice.call(arguments).join(", ") + "\n" + new Error().stack), d = !1), c.apply(this, arguments);
	    }, c);
	  }function v(b, c) {
	    null != a.deprecationHandler && a.deprecationHandler(b, c), jd[b] || (t(c), jd[b] = !0);
	  }function w(a) {
	    return a instanceof Function || "[object Function]" === Object.prototype.toString.call(a);
	  }function x(a) {
	    return "[object Object]" === Object.prototype.toString.call(a);
	  }function y(a) {
	    var b, c;for (c in a) {
	      b = a[c], w(b) ? this[c] = b : this["_" + c] = b;
	    }this._config = a, this._ordinalParseLenient = new RegExp(this._ordinalParse.source + "|" + /\d{1,2}/.source);
	  }function z(a, b) {
	    var c,
	        d = g({}, a);for (c in b) {
	      f(b, c) && (x(a[c]) && x(b[c]) ? (d[c] = {}, g(d[c], a[c]), g(d[c], b[c])) : null != b[c] ? d[c] = b[c] : delete d[c]);
	    }return d;
	  }function A(a) {
	    null != a && this.set(a);
	  }function B(a) {
	    return a ? a.toLowerCase().replace("_", "-") : a;
	  }function C(a) {
	    for (var b, c, d, e, f = 0; f < a.length;) {
	      for (e = B(a[f]).split("-"), b = e.length, c = B(a[f + 1]), c = c ? c.split("-") : null; b > 0;) {
	        if (d = D(e.slice(0, b).join("-"))) return d;if (c && c.length >= b && s(e, c, !0) >= b - 1) break;b--;
	      }f++;
	    }return null;
	  }function D(a) {
	    var b = null;if (!nd[a] && "undefined" != typeof module && module && module.exports) try {
	      b = ld._abbr, !(function webpackMissingModule() { var e = new Error("Cannot find module \"./locale\""); e.code = 'MODULE_NOT_FOUND'; throw e; }()), E(b);
	    } catch (c) {}return nd[a];
	  }function E(a, b) {
	    var c;return a && (c = m(b) ? H(a) : F(a, b), c && (ld = c)), ld._abbr;
	  }function F(a, b) {
	    return null !== b ? (b.abbr = a, null != nd[a] ? (v("defineLocaleOverride", "use moment.updateLocale(localeName, config) to change an existing locale. moment.defineLocale(localeName, config) should only be used for creating a new locale"), b = z(nd[a]._config, b)) : null != b.parentLocale && (null != nd[b.parentLocale] ? b = z(nd[b.parentLocale]._config, b) : v("parentLocaleUndefined", "specified parentLocale is not defined yet")), nd[a] = new A(b), E(a), nd[a]) : (delete nd[a], null);
	  }function G(a, b) {
	    if (null != b) {
	      var c;null != nd[a] && (b = z(nd[a]._config, b)), c = new A(b), c.parentLocale = nd[a], nd[a] = c, E(a);
	    } else null != nd[a] && (null != nd[a].parentLocale ? nd[a] = nd[a].parentLocale : null != nd[a] && delete nd[a]);return nd[a];
	  }function H(a) {
	    var b;if (a && a._locale && a._locale._abbr && (a = a._locale._abbr), !a) return ld;if (!c(a)) {
	      if (b = D(a)) return b;a = [a];
	    }return C(a);
	  }function I() {
	    return kd(nd);
	  }function J(a, b) {
	    var c = a.toLowerCase();od[c] = od[c + "s"] = od[b] = a;
	  }function K(a) {
	    return "string" == typeof a ? od[a] || od[a.toLowerCase()] : void 0;
	  }function L(a) {
	    var b,
	        c,
	        d = {};for (c in a) {
	      f(a, c) && (b = K(c), b && (d[b] = a[c]));
	    }return d;
	  }function M(b, c) {
	    return function (d) {
	      return null != d ? (O(this, b, d), a.updateOffset(this, c), this) : N(this, b);
	    };
	  }function N(a, b) {
	    return a.isValid() ? a._d["get" + (a._isUTC ? "UTC" : "") + b]() : NaN;
	  }function O(a, b, c) {
	    a.isValid() && a._d["set" + (a._isUTC ? "UTC" : "") + b](c);
	  }function P(a, b) {
	    var c;if ("object" == (typeof a === "undefined" ? "undefined" : _typeof(a))) for (c in a) {
	      this.set(c, a[c]);
	    } else if (a = K(a), w(this[a])) return this[a](b);return this;
	  }function Q(a, b, c) {
	    var d = "" + Math.abs(a),
	        e = b - d.length,
	        f = a >= 0;return (f ? c ? "+" : "" : "-") + Math.pow(10, Math.max(0, e)).toString().substr(1) + d;
	  }function R(a, b, c, d) {
	    var e = d;"string" == typeof d && (e = function e() {
	      return this[d]();
	    }), a && (sd[a] = e), b && (sd[b[0]] = function () {
	      return Q(e.apply(this, arguments), b[1], b[2]);
	    }), c && (sd[c] = function () {
	      return this.localeData().ordinal(e.apply(this, arguments), a);
	    });
	  }function S(a) {
	    return a.match(/\[[\s\S]/) ? a.replace(/^\[|\]$/g, "") : a.replace(/\\/g, "");
	  }function T(a) {
	    var b,
	        c,
	        d = a.match(pd);for (b = 0, c = d.length; c > b; b++) {
	      sd[d[b]] ? d[b] = sd[d[b]] : d[b] = S(d[b]);
	    }return function (b) {
	      var e,
	          f = "";for (e = 0; c > e; e++) {
	        f += d[e] instanceof Function ? d[e].call(b, a) : d[e];
	      }return f;
	    };
	  }function U(a, b) {
	    return a.isValid() ? (b = V(b, a.localeData()), rd[b] = rd[b] || T(b), rd[b](a)) : a.localeData().invalidDate();
	  }function V(a, b) {
	    function c(a) {
	      return b.longDateFormat(a) || a;
	    }var d = 5;for (qd.lastIndex = 0; d >= 0 && qd.test(a);) {
	      a = a.replace(qd, c), qd.lastIndex = 0, d -= 1;
	    }return a;
	  }function W(a, b, c) {
	    Kd[a] = w(b) ? b : function (a, d) {
	      return a && c ? c : b;
	    };
	  }function X(a, b) {
	    return f(Kd, a) ? Kd[a](b._strict, b._locale) : new RegExp(Y(a));
	  }function Y(a) {
	    return Z(a.replace("\\", "").replace(/\\(\[)|\\(\])|\[([^\]\[]*)\]|\\(.)/g, function (a, b, c, d, e) {
	      return b || c || d || e;
	    }));
	  }function Z(a) {
	    return a.replace(/[-\/\\^$*+?.()|[\]{}]/g, "\\$&");
	  }function $(a, b) {
	    var c,
	        d = b;for ("string" == typeof a && (a = [a]), "number" == typeof b && (d = function d(a, c) {
	      c[b] = r(a);
	    }), c = 0; c < a.length; c++) {
	      Ld[a[c]] = d;
	    }
	  }function _(a, b) {
	    $(a, function (a, c, d, e) {
	      d._w = d._w || {}, b(a, d._w, d, e);
	    });
	  }function aa(a, b, c) {
	    null != b && f(Ld, a) && Ld[a](b, c._a, c, a);
	  }function ba(a, b) {
	    return new Date(Date.UTC(a, b + 1, 0)).getUTCDate();
	  }function ca(a, b) {
	    return c(this._months) ? this._months[a.month()] : this._months[Vd.test(b) ? "format" : "standalone"][a.month()];
	  }function da(a, b) {
	    return c(this._monthsShort) ? this._monthsShort[a.month()] : this._monthsShort[Vd.test(b) ? "format" : "standalone"][a.month()];
	  }function ea(a, b, c) {
	    var d,
	        e,
	        f,
	        g = a.toLocaleLowerCase();if (!this._monthsParse) for (this._monthsParse = [], this._longMonthsParse = [], this._shortMonthsParse = [], d = 0; 12 > d; ++d) {
	      f = h([2e3, d]), this._shortMonthsParse[d] = this.monthsShort(f, "").toLocaleLowerCase(), this._longMonthsParse[d] = this.months(f, "").toLocaleLowerCase();
	    }return c ? "MMM" === b ? (e = md.call(this._shortMonthsParse, g), -1 !== e ? e : null) : (e = md.call(this._longMonthsParse, g), -1 !== e ? e : null) : "MMM" === b ? (e = md.call(this._shortMonthsParse, g), -1 !== e ? e : (e = md.call(this._longMonthsParse, g), -1 !== e ? e : null)) : (e = md.call(this._longMonthsParse, g), -1 !== e ? e : (e = md.call(this._shortMonthsParse, g), -1 !== e ? e : null));
	  }function fa(a, b, c) {
	    var d, e, f;if (this._monthsParseExact) return ea.call(this, a, b, c);for (this._monthsParse || (this._monthsParse = [], this._longMonthsParse = [], this._shortMonthsParse = []), d = 0; 12 > d; d++) {
	      if (e = h([2e3, d]), c && !this._longMonthsParse[d] && (this._longMonthsParse[d] = new RegExp("^" + this.months(e, "").replace(".", "") + "$", "i"), this._shortMonthsParse[d] = new RegExp("^" + this.monthsShort(e, "").replace(".", "") + "$", "i")), c || this._monthsParse[d] || (f = "^" + this.months(e, "") + "|^" + this.monthsShort(e, ""), this._monthsParse[d] = new RegExp(f.replace(".", ""), "i")), c && "MMMM" === b && this._longMonthsParse[d].test(a)) return d;if (c && "MMM" === b && this._shortMonthsParse[d].test(a)) return d;if (!c && this._monthsParse[d].test(a)) return d;
	    }
	  }function ga(a, b) {
	    var c;if (!a.isValid()) return a;if ("string" == typeof b) if (/^\d+$/.test(b)) b = r(b);else if (b = a.localeData().monthsParse(b), "number" != typeof b) return a;return c = Math.min(a.date(), ba(a.year(), b)), a._d["set" + (a._isUTC ? "UTC" : "") + "Month"](b, c), a;
	  }function ha(b) {
	    return null != b ? (ga(this, b), a.updateOffset(this, !0), this) : N(this, "Month");
	  }function ia() {
	    return ba(this.year(), this.month());
	  }function ja(a) {
	    return this._monthsParseExact ? (f(this, "_monthsRegex") || la.call(this), a ? this._monthsShortStrictRegex : this._monthsShortRegex) : this._monthsShortStrictRegex && a ? this._monthsShortStrictRegex : this._monthsShortRegex;
	  }function ka(a) {
	    return this._monthsParseExact ? (f(this, "_monthsRegex") || la.call(this), a ? this._monthsStrictRegex : this._monthsRegex) : this._monthsStrictRegex && a ? this._monthsStrictRegex : this._monthsRegex;
	  }function la() {
	    function a(a, b) {
	      return b.length - a.length;
	    }var b,
	        c,
	        d = [],
	        e = [],
	        f = [];for (b = 0; 12 > b; b++) {
	      c = h([2e3, b]), d.push(this.monthsShort(c, "")), e.push(this.months(c, "")), f.push(this.months(c, "")), f.push(this.monthsShort(c, ""));
	    }for (d.sort(a), e.sort(a), f.sort(a), b = 0; 12 > b; b++) {
	      d[b] = Z(d[b]), e[b] = Z(e[b]), f[b] = Z(f[b]);
	    }this._monthsRegex = new RegExp("^(" + f.join("|") + ")", "i"), this._monthsShortRegex = this._monthsRegex, this._monthsStrictRegex = new RegExp("^(" + e.join("|") + ")", "i"), this._monthsShortStrictRegex = new RegExp("^(" + d.join("|") + ")", "i");
	  }function ma(a) {
	    var b,
	        c = a._a;return c && -2 === j(a).overflow && (b = c[Nd] < 0 || c[Nd] > 11 ? Nd : c[Od] < 1 || c[Od] > ba(c[Md], c[Nd]) ? Od : c[Pd] < 0 || c[Pd] > 24 || 24 === c[Pd] && (0 !== c[Qd] || 0 !== c[Rd] || 0 !== c[Sd]) ? Pd : c[Qd] < 0 || c[Qd] > 59 ? Qd : c[Rd] < 0 || c[Rd] > 59 ? Rd : c[Sd] < 0 || c[Sd] > 999 ? Sd : -1, j(a)._overflowDayOfYear && (Md > b || b > Od) && (b = Od), j(a)._overflowWeeks && -1 === b && (b = Td), j(a)._overflowWeekday && -1 === b && (b = Ud), j(a).overflow = b), a;
	  }function na(a) {
	    var b,
	        c,
	        d,
	        e,
	        f,
	        g,
	        h = a._i,
	        i = $d.exec(h) || _d.exec(h);if (i) {
	      for (j(a).iso = !0, b = 0, c = be.length; c > b; b++) {
	        if (be[b][1].exec(i[1])) {
	          e = be[b][0], d = be[b][2] !== !1;break;
	        }
	      }if (null == e) return void (a._isValid = !1);if (i[3]) {
	        for (b = 0, c = ce.length; c > b; b++) {
	          if (ce[b][1].exec(i[3])) {
	            f = (i[2] || " ") + ce[b][0];break;
	          }
	        }if (null == f) return void (a._isValid = !1);
	      }if (!d && null != f) return void (a._isValid = !1);if (i[4]) {
	        if (!ae.exec(i[4])) return void (a._isValid = !1);g = "Z";
	      }a._f = e + (f || "") + (g || ""), Ca(a);
	    } else a._isValid = !1;
	  }function oa(b) {
	    var c = de.exec(b._i);return null !== c ? void (b._d = new Date(+c[1])) : (na(b), void (b._isValid === !1 && (delete b._isValid, a.createFromInputFallback(b))));
	  }function pa(a, b, c, d, e, f, g) {
	    var h = new Date(a, b, c, d, e, f, g);return 100 > a && a >= 0 && isFinite(h.getFullYear()) && h.setFullYear(a), h;
	  }function qa(a) {
	    var b = new Date(Date.UTC.apply(null, arguments));return 100 > a && a >= 0 && isFinite(b.getUTCFullYear()) && b.setUTCFullYear(a), b;
	  }function ra(a) {
	    return sa(a) ? 366 : 365;
	  }function sa(a) {
	    return a % 4 === 0 && a % 100 !== 0 || a % 400 === 0;
	  }function ta() {
	    return sa(this.year());
	  }function ua(a, b, c) {
	    var d = 7 + b - c,
	        e = (7 + qa(a, 0, d).getUTCDay() - b) % 7;return -e + d - 1;
	  }function va(a, b, c, d, e) {
	    var f,
	        g,
	        h = (7 + c - d) % 7,
	        i = ua(a, d, e),
	        j = 1 + 7 * (b - 1) + h + i;return 0 >= j ? (f = a - 1, g = ra(f) + j) : j > ra(a) ? (f = a + 1, g = j - ra(a)) : (f = a, g = j), { year: f, dayOfYear: g };
	  }function wa(a, b, c) {
	    var d,
	        e,
	        f = ua(a.year(), b, c),
	        g = Math.floor((a.dayOfYear() - f - 1) / 7) + 1;return 1 > g ? (e = a.year() - 1, d = g + xa(e, b, c)) : g > xa(a.year(), b, c) ? (d = g - xa(a.year(), b, c), e = a.year() + 1) : (e = a.year(), d = g), { week: d, year: e };
	  }function xa(a, b, c) {
	    var d = ua(a, b, c),
	        e = ua(a + 1, b, c);return (ra(a) - d + e) / 7;
	  }function ya(a, b, c) {
	    return null != a ? a : null != b ? b : c;
	  }function za(b) {
	    var c = new Date(a.now());return b._useUTC ? [c.getUTCFullYear(), c.getUTCMonth(), c.getUTCDate()] : [c.getFullYear(), c.getMonth(), c.getDate()];
	  }function Aa(a) {
	    var b,
	        c,
	        d,
	        e,
	        f = [];if (!a._d) {
	      for (d = za(a), a._w && null == a._a[Od] && null == a._a[Nd] && Ba(a), a._dayOfYear && (e = ya(a._a[Md], d[Md]), a._dayOfYear > ra(e) && (j(a)._overflowDayOfYear = !0), c = qa(e, 0, a._dayOfYear), a._a[Nd] = c.getUTCMonth(), a._a[Od] = c.getUTCDate()), b = 0; 3 > b && null == a._a[b]; ++b) {
	        a._a[b] = f[b] = d[b];
	      }for (; 7 > b; b++) {
	        a._a[b] = f[b] = null == a._a[b] ? 2 === b ? 1 : 0 : a._a[b];
	      }24 === a._a[Pd] && 0 === a._a[Qd] && 0 === a._a[Rd] && 0 === a._a[Sd] && (a._nextDay = !0, a._a[Pd] = 0), a._d = (a._useUTC ? qa : pa).apply(null, f), null != a._tzm && a._d.setUTCMinutes(a._d.getUTCMinutes() - a._tzm), a._nextDay && (a._a[Pd] = 24);
	    }
	  }function Ba(a) {
	    var b, c, d, e, f, g, h, i;b = a._w, null != b.GG || null != b.W || null != b.E ? (f = 1, g = 4, c = ya(b.GG, a._a[Md], wa(Ka(), 1, 4).year), d = ya(b.W, 1), e = ya(b.E, 1), (1 > e || e > 7) && (i = !0)) : (f = a._locale._week.dow, g = a._locale._week.doy, c = ya(b.gg, a._a[Md], wa(Ka(), f, g).year), d = ya(b.w, 1), null != b.d ? (e = b.d, (0 > e || e > 6) && (i = !0)) : null != b.e ? (e = b.e + f, (b.e < 0 || b.e > 6) && (i = !0)) : e = f), 1 > d || d > xa(c, f, g) ? j(a)._overflowWeeks = !0 : null != i ? j(a)._overflowWeekday = !0 : (h = va(c, d, e, f, g), a._a[Md] = h.year, a._dayOfYear = h.dayOfYear);
	  }function Ca(b) {
	    if (b._f === a.ISO_8601) return void na(b);b._a = [], j(b).empty = !0;var c,
	        d,
	        e,
	        f,
	        g,
	        h = "" + b._i,
	        i = h.length,
	        k = 0;for (e = V(b._f, b._locale).match(pd) || [], c = 0; c < e.length; c++) {
	      f = e[c], d = (h.match(X(f, b)) || [])[0], d && (g = h.substr(0, h.indexOf(d)), g.length > 0 && j(b).unusedInput.push(g), h = h.slice(h.indexOf(d) + d.length), k += d.length), sd[f] ? (d ? j(b).empty = !1 : j(b).unusedTokens.push(f), aa(f, d, b)) : b._strict && !d && j(b).unusedTokens.push(f);
	    }j(b).charsLeftOver = i - k, h.length > 0 && j(b).unusedInput.push(h), j(b).bigHour === !0 && b._a[Pd] <= 12 && b._a[Pd] > 0 && (j(b).bigHour = void 0), j(b).parsedDateParts = b._a.slice(0), j(b).meridiem = b._meridiem, b._a[Pd] = Da(b._locale, b._a[Pd], b._meridiem), Aa(b), ma(b);
	  }function Da(a, b, c) {
	    var d;return null == c ? b : null != a.meridiemHour ? a.meridiemHour(b, c) : null != a.isPM ? (d = a.isPM(c), d && 12 > b && (b += 12), d || 12 !== b || (b = 0), b) : b;
	  }function Ea(a) {
	    var b, c, d, e, f;if (0 === a._f.length) return j(a).invalidFormat = !0, void (a._d = new Date(NaN));for (e = 0; e < a._f.length; e++) {
	      f = 0, b = n({}, a), null != a._useUTC && (b._useUTC = a._useUTC), b._f = a._f[e], Ca(b), k(b) && (f += j(b).charsLeftOver, f += 10 * j(b).unusedTokens.length, j(b).score = f, (null == d || d > f) && (d = f, c = b));
	    }g(a, c || b);
	  }function Fa(a) {
	    if (!a._d) {
	      var b = L(a._i);a._a = e([b.year, b.month, b.day || b.date, b.hour, b.minute, b.second, b.millisecond], function (a) {
	        return a && parseInt(a, 10);
	      }), Aa(a);
	    }
	  }function Ga(a) {
	    var b = new o(ma(Ha(a)));return b._nextDay && (b.add(1, "d"), b._nextDay = void 0), b;
	  }function Ha(a) {
	    var b = a._i,
	        e = a._f;return a._locale = a._locale || H(a._l), null === b || void 0 === e && "" === b ? l({ nullInput: !0 }) : ("string" == typeof b && (a._i = b = a._locale.preparse(b)), p(b) ? new o(ma(b)) : (c(e) ? Ea(a) : e ? Ca(a) : d(b) ? a._d = b : Ia(a), k(a) || (a._d = null), a));
	  }function Ia(b) {
	    var f = b._i;void 0 === f ? b._d = new Date(a.now()) : d(f) ? b._d = new Date(f.valueOf()) : "string" == typeof f ? oa(b) : c(f) ? (b._a = e(f.slice(0), function (a) {
	      return parseInt(a, 10);
	    }), Aa(b)) : "object" == (typeof f === "undefined" ? "undefined" : _typeof(f)) ? Fa(b) : "number" == typeof f ? b._d = new Date(f) : a.createFromInputFallback(b);
	  }function Ja(a, b, c, d, e) {
	    var f = {};return "boolean" == typeof c && (d = c, c = void 0), f._isAMomentObject = !0, f._useUTC = f._isUTC = e, f._l = c, f._i = a, f._f = b, f._strict = d, Ga(f);
	  }function Ka(a, b, c, d) {
	    return Ja(a, b, c, d, !1);
	  }function La(a, b) {
	    var d, e;if (1 === b.length && c(b[0]) && (b = b[0]), !b.length) return Ka();for (d = b[0], e = 1; e < b.length; ++e) {
	      (!b[e].isValid() || b[e][a](d)) && (d = b[e]);
	    }return d;
	  }function Ma() {
	    var a = [].slice.call(arguments, 0);return La("isBefore", a);
	  }function Na() {
	    var a = [].slice.call(arguments, 0);return La("isAfter", a);
	  }function Oa(a) {
	    var b = L(a),
	        c = b.year || 0,
	        d = b.quarter || 0,
	        e = b.month || 0,
	        f = b.week || 0,
	        g = b.day || 0,
	        h = b.hour || 0,
	        i = b.minute || 0,
	        j = b.second || 0,
	        k = b.millisecond || 0;this._milliseconds = +k + 1e3 * j + 6e4 * i + 1e3 * h * 60 * 60, this._days = +g + 7 * f, this._months = +e + 3 * d + 12 * c, this._data = {}, this._locale = H(), this._bubble();
	  }function Pa(a) {
	    return a instanceof Oa;
	  }function Qa(a, b) {
	    R(a, 0, 0, function () {
	      var a = this.utcOffset(),
	          c = "+";return 0 > a && (a = -a, c = "-"), c + Q(~~(a / 60), 2) + b + Q(~~a % 60, 2);
	    });
	  }function Ra(a, b) {
	    var c = (b || "").match(a) || [],
	        d = c[c.length - 1] || [],
	        e = (d + "").match(ie) || ["-", 0, 0],
	        f = +(60 * e[1]) + r(e[2]);return "+" === e[0] ? f : -f;
	  }function Sa(b, c) {
	    var e, f;return c._isUTC ? (e = c.clone(), f = (p(b) || d(b) ? b.valueOf() : Ka(b).valueOf()) - e.valueOf(), e._d.setTime(e._d.valueOf() + f), a.updateOffset(e, !1), e) : Ka(b).local();
	  }function Ta(a) {
	    return 15 * -Math.round(a._d.getTimezoneOffset() / 15);
	  }function Ua(b, c) {
	    var d,
	        e = this._offset || 0;return this.isValid() ? null != b ? ("string" == typeof b ? b = Ra(Hd, b) : Math.abs(b) < 16 && (b = 60 * b), !this._isUTC && c && (d = Ta(this)), this._offset = b, this._isUTC = !0, null != d && this.add(d, "m"), e !== b && (!c || this._changeInProgress ? jb(this, db(b - e, "m"), 1, !1) : this._changeInProgress || (this._changeInProgress = !0, a.updateOffset(this, !0), this._changeInProgress = null)), this) : this._isUTC ? e : Ta(this) : null != b ? this : NaN;
	  }function Va(a, b) {
	    return null != a ? ("string" != typeof a && (a = -a), this.utcOffset(a, b), this) : -this.utcOffset();
	  }function Wa(a) {
	    return this.utcOffset(0, a);
	  }function Xa(a) {
	    return this._isUTC && (this.utcOffset(0, a), this._isUTC = !1, a && this.subtract(Ta(this), "m")), this;
	  }function Ya() {
	    return this._tzm ? this.utcOffset(this._tzm) : "string" == typeof this._i && this.utcOffset(Ra(Gd, this._i)), this;
	  }function Za(a) {
	    return this.isValid() ? (a = a ? Ka(a).utcOffset() : 0, (this.utcOffset() - a) % 60 === 0) : !1;
	  }function $a() {
	    return this.utcOffset() > this.clone().month(0).utcOffset() || this.utcOffset() > this.clone().month(5).utcOffset();
	  }function _a() {
	    if (!m(this._isDSTShifted)) return this._isDSTShifted;var a = {};if (n(a, this), a = Ha(a), a._a) {
	      var b = a._isUTC ? h(a._a) : Ka(a._a);this._isDSTShifted = this.isValid() && s(a._a, b.toArray()) > 0;
	    } else this._isDSTShifted = !1;return this._isDSTShifted;
	  }function ab() {
	    return this.isValid() ? !this._isUTC : !1;
	  }function bb() {
	    return this.isValid() ? this._isUTC : !1;
	  }function cb() {
	    return this.isValid() ? this._isUTC && 0 === this._offset : !1;
	  }function db(a, b) {
	    var c,
	        d,
	        e,
	        g = a,
	        h = null;return Pa(a) ? g = { ms: a._milliseconds, d: a._days, M: a._months } : "number" == typeof a ? (g = {}, b ? g[b] = a : g.milliseconds = a) : (h = je.exec(a)) ? (c = "-" === h[1] ? -1 : 1, g = { y: 0, d: r(h[Od]) * c, h: r(h[Pd]) * c, m: r(h[Qd]) * c, s: r(h[Rd]) * c, ms: r(h[Sd]) * c }) : (h = ke.exec(a)) ? (c = "-" === h[1] ? -1 : 1, g = { y: eb(h[2], c), M: eb(h[3], c), w: eb(h[4], c), d: eb(h[5], c), h: eb(h[6], c), m: eb(h[7], c), s: eb(h[8], c) }) : null == g ? g = {} : "object" == (typeof g === "undefined" ? "undefined" : _typeof(g)) && ("from" in g || "to" in g) && (e = gb(Ka(g.from), Ka(g.to)), g = {}, g.ms = e.milliseconds, g.M = e.months), d = new Oa(g), Pa(a) && f(a, "_locale") && (d._locale = a._locale), d;
	  }function eb(a, b) {
	    var c = a && parseFloat(a.replace(",", "."));return (isNaN(c) ? 0 : c) * b;
	  }function fb(a, b) {
	    var c = { milliseconds: 0, months: 0 };return c.months = b.month() - a.month() + 12 * (b.year() - a.year()), a.clone().add(c.months, "M").isAfter(b) && --c.months, c.milliseconds = +b - +a.clone().add(c.months, "M"), c;
	  }function gb(a, b) {
	    var c;return a.isValid() && b.isValid() ? (b = Sa(b, a), a.isBefore(b) ? c = fb(a, b) : (c = fb(b, a), c.milliseconds = -c.milliseconds, c.months = -c.months), c) : { milliseconds: 0, months: 0 };
	  }function hb(a) {
	    return 0 > a ? -1 * Math.round(-1 * a) : Math.round(a);
	  }function ib(a, b) {
	    return function (c, d) {
	      var e, f;return null === d || isNaN(+d) || (v(b, "moment()." + b + "(period, number) is deprecated. Please use moment()." + b + "(number, period)."), f = c, c = d, d = f), c = "string" == typeof c ? +c : c, e = db(c, d), jb(this, e, a), this;
	    };
	  }function jb(b, c, d, e) {
	    var f = c._milliseconds,
	        g = hb(c._days),
	        h = hb(c._months);b.isValid() && (e = null == e ? !0 : e, f && b._d.setTime(b._d.valueOf() + f * d), g && O(b, "Date", N(b, "Date") + g * d), h && ga(b, N(b, "Month") + h * d), e && a.updateOffset(b, g || h));
	  }function kb(a, b) {
	    var c = a || Ka(),
	        d = Sa(c, this).startOf("day"),
	        e = this.diff(d, "days", !0),
	        f = -6 > e ? "sameElse" : -1 > e ? "lastWeek" : 0 > e ? "lastDay" : 1 > e ? "sameDay" : 2 > e ? "nextDay" : 7 > e ? "nextWeek" : "sameElse",
	        g = b && (w(b[f]) ? b[f]() : b[f]);return this.format(g || this.localeData().calendar(f, this, Ka(c)));
	  }function lb() {
	    return new o(this);
	  }function mb(a, b) {
	    var c = p(a) ? a : Ka(a);return this.isValid() && c.isValid() ? (b = K(m(b) ? "millisecond" : b), "millisecond" === b ? this.valueOf() > c.valueOf() : c.valueOf() < this.clone().startOf(b).valueOf()) : !1;
	  }function nb(a, b) {
	    var c = p(a) ? a : Ka(a);return this.isValid() && c.isValid() ? (b = K(m(b) ? "millisecond" : b), "millisecond" === b ? this.valueOf() < c.valueOf() : this.clone().endOf(b).valueOf() < c.valueOf()) : !1;
	  }function ob(a, b, c, d) {
	    return d = d || "()", ("(" === d[0] ? this.isAfter(a, c) : !this.isBefore(a, c)) && (")" === d[1] ? this.isBefore(b, c) : !this.isAfter(b, c));
	  }function pb(a, b) {
	    var c,
	        d = p(a) ? a : Ka(a);return this.isValid() && d.isValid() ? (b = K(b || "millisecond"), "millisecond" === b ? this.valueOf() === d.valueOf() : (c = d.valueOf(), this.clone().startOf(b).valueOf() <= c && c <= this.clone().endOf(b).valueOf())) : !1;
	  }function qb(a, b) {
	    return this.isSame(a, b) || this.isAfter(a, b);
	  }function rb(a, b) {
	    return this.isSame(a, b) || this.isBefore(a, b);
	  }function sb(a, b, c) {
	    var d, e, f, g;return this.isValid() ? (d = Sa(a, this), d.isValid() ? (e = 6e4 * (d.utcOffset() - this.utcOffset()), b = K(b), "year" === b || "month" === b || "quarter" === b ? (g = tb(this, d), "quarter" === b ? g /= 3 : "year" === b && (g /= 12)) : (f = this - d, g = "second" === b ? f / 1e3 : "minute" === b ? f / 6e4 : "hour" === b ? f / 36e5 : "day" === b ? (f - e) / 864e5 : "week" === b ? (f - e) / 6048e5 : f), c ? g : q(g)) : NaN) : NaN;
	  }function tb(a, b) {
	    var c,
	        d,
	        e = 12 * (b.year() - a.year()) + (b.month() - a.month()),
	        f = a.clone().add(e, "months");return 0 > b - f ? (c = a.clone().add(e - 1, "months"), d = (b - f) / (f - c)) : (c = a.clone().add(e + 1, "months"), d = (b - f) / (c - f)), -(e + d) || 0;
	  }function ub() {
	    return this.clone().locale("en").format("ddd MMM DD YYYY HH:mm:ss [GMT]ZZ");
	  }function vb() {
	    var a = this.clone().utc();return 0 < a.year() && a.year() <= 9999 ? w(Date.prototype.toISOString) ? this.toDate().toISOString() : U(a, "YYYY-MM-DD[T]HH:mm:ss.SSS[Z]") : U(a, "YYYYYY-MM-DD[T]HH:mm:ss.SSS[Z]");
	  }function wb(b) {
	    b || (b = this.isUtc() ? a.defaultFormatUtc : a.defaultFormat);var c = U(this, b);return this.localeData().postformat(c);
	  }function xb(a, b) {
	    return this.isValid() && (p(a) && a.isValid() || Ka(a).isValid()) ? db({ to: this, from: a }).locale(this.locale()).humanize(!b) : this.localeData().invalidDate();
	  }function yb(a) {
	    return this.from(Ka(), a);
	  }function zb(a, b) {
	    return this.isValid() && (p(a) && a.isValid() || Ka(a).isValid()) ? db({ from: this, to: a }).locale(this.locale()).humanize(!b) : this.localeData().invalidDate();
	  }function Ab(a) {
	    return this.to(Ka(), a);
	  }function Bb(a) {
	    var b;return void 0 === a ? this._locale._abbr : (b = H(a), null != b && (this._locale = b), this);
	  }function Cb() {
	    return this._locale;
	  }function Db(a) {
	    switch (a = K(a)) {case "year":
	        this.month(0);case "quarter":case "month":
	        this.date(1);case "week":case "isoWeek":case "day":case "date":
	        this.hours(0);case "hour":
	        this.minutes(0);case "minute":
	        this.seconds(0);case "second":
	        this.milliseconds(0);}return "week" === a && this.weekday(0), "isoWeek" === a && this.isoWeekday(1), "quarter" === a && this.month(3 * Math.floor(this.month() / 3)), this;
	  }function Eb(a) {
	    return a = K(a), void 0 === a || "millisecond" === a ? this : ("date" === a && (a = "day"), this.startOf(a).add(1, "isoWeek" === a ? "week" : a).subtract(1, "ms"));
	  }function Fb() {
	    return this._d.valueOf() - 6e4 * (this._offset || 0);
	  }function Gb() {
	    return Math.floor(this.valueOf() / 1e3);
	  }function Hb() {
	    return this._offset ? new Date(this.valueOf()) : this._d;
	  }function Ib() {
	    var a = this;return [a.year(), a.month(), a.date(), a.hour(), a.minute(), a.second(), a.millisecond()];
	  }function Jb() {
	    var a = this;return { years: a.year(), months: a.month(), date: a.date(), hours: a.hours(), minutes: a.minutes(), seconds: a.seconds(), milliseconds: a.milliseconds() };
	  }function Kb() {
	    return this.isValid() ? this.toISOString() : null;
	  }function Lb() {
	    return k(this);
	  }function Mb() {
	    return g({}, j(this));
	  }function Nb() {
	    return j(this).overflow;
	  }function Ob() {
	    return { input: this._i, format: this._f, locale: this._locale, isUTC: this._isUTC, strict: this._strict };
	  }function Pb(a, b) {
	    R(0, [a, a.length], 0, b);
	  }function Qb(a) {
	    return Ub.call(this, a, this.week(), this.weekday(), this.localeData()._week.dow, this.localeData()._week.doy);
	  }function Rb(a) {
	    return Ub.call(this, a, this.isoWeek(), this.isoWeekday(), 1, 4);
	  }function Sb() {
	    return xa(this.year(), 1, 4);
	  }function Tb() {
	    var a = this.localeData()._week;return xa(this.year(), a.dow, a.doy);
	  }function Ub(a, b, c, d, e) {
	    var f;return null == a ? wa(this, d, e).year : (f = xa(a, d, e), b > f && (b = f), Vb.call(this, a, b, c, d, e));
	  }function Vb(a, b, c, d, e) {
	    var f = va(a, b, c, d, e),
	        g = qa(f.year, 0, f.dayOfYear);return this.year(g.getUTCFullYear()), this.month(g.getUTCMonth()), this.date(g.getUTCDate()), this;
	  }function Wb(a) {
	    return null == a ? Math.ceil((this.month() + 1) / 3) : this.month(3 * (a - 1) + this.month() % 3);
	  }function Xb(a) {
	    return wa(a, this._week.dow, this._week.doy).week;
	  }function Yb() {
	    return this._week.dow;
	  }function Zb() {
	    return this._week.doy;
	  }function $b(a) {
	    var b = this.localeData().week(this);return null == a ? b : this.add(7 * (a - b), "d");
	  }function _b(a) {
	    var b = wa(this, 1, 4).week;return null == a ? b : this.add(7 * (a - b), "d");
	  }function ac(a, b) {
	    return "string" != typeof a ? a : isNaN(a) ? (a = b.weekdaysParse(a), "number" == typeof a ? a : null) : parseInt(a, 10);
	  }function bc(a, b) {
	    return c(this._weekdays) ? this._weekdays[a.day()] : this._weekdays[this._weekdays.isFormat.test(b) ? "format" : "standalone"][a.day()];
	  }function cc(a) {
	    return this._weekdaysShort[a.day()];
	  }function dc(a) {
	    return this._weekdaysMin[a.day()];
	  }function ec(a, b, c) {
	    var d,
	        e,
	        f,
	        g = a.toLocaleLowerCase();if (!this._weekdaysParse) for (this._weekdaysParse = [], this._shortWeekdaysParse = [], this._minWeekdaysParse = [], d = 0; 7 > d; ++d) {
	      f = h([2e3, 1]).day(d), this._minWeekdaysParse[d] = this.weekdaysMin(f, "").toLocaleLowerCase(), this._shortWeekdaysParse[d] = this.weekdaysShort(f, "").toLocaleLowerCase(), this._weekdaysParse[d] = this.weekdays(f, "").toLocaleLowerCase();
	    }return c ? "dddd" === b ? (e = md.call(this._weekdaysParse, g), -1 !== e ? e : null) : "ddd" === b ? (e = md.call(this._shortWeekdaysParse, g), -1 !== e ? e : null) : (e = md.call(this._minWeekdaysParse, g), -1 !== e ? e : null) : "dddd" === b ? (e = md.call(this._weekdaysParse, g), -1 !== e ? e : (e = md.call(this._shortWeekdaysParse, g), -1 !== e ? e : (e = md.call(this._minWeekdaysParse, g), -1 !== e ? e : null))) : "ddd" === b ? (e = md.call(this._shortWeekdaysParse, g), -1 !== e ? e : (e = md.call(this._weekdaysParse, g), -1 !== e ? e : (e = md.call(this._minWeekdaysParse, g), -1 !== e ? e : null))) : (e = md.call(this._minWeekdaysParse, g), -1 !== e ? e : (e = md.call(this._weekdaysParse, g), -1 !== e ? e : (e = md.call(this._shortWeekdaysParse, g), -1 !== e ? e : null)));
	  }function fc(a, b, c) {
	    var d, e, f;if (this._weekdaysParseExact) return ec.call(this, a, b, c);for (this._weekdaysParse || (this._weekdaysParse = [], this._minWeekdaysParse = [], this._shortWeekdaysParse = [], this._fullWeekdaysParse = []), d = 0; 7 > d; d++) {
	      if (e = h([2e3, 1]).day(d), c && !this._fullWeekdaysParse[d] && (this._fullWeekdaysParse[d] = new RegExp("^" + this.weekdays(e, "").replace(".", ".?") + "$", "i"), this._shortWeekdaysParse[d] = new RegExp("^" + this.weekdaysShort(e, "").replace(".", ".?") + "$", "i"), this._minWeekdaysParse[d] = new RegExp("^" + this.weekdaysMin(e, "").replace(".", ".?") + "$", "i")), this._weekdaysParse[d] || (f = "^" + this.weekdays(e, "") + "|^" + this.weekdaysShort(e, "") + "|^" + this.weekdaysMin(e, ""), this._weekdaysParse[d] = new RegExp(f.replace(".", ""), "i")), c && "dddd" === b && this._fullWeekdaysParse[d].test(a)) return d;if (c && "ddd" === b && this._shortWeekdaysParse[d].test(a)) return d;if (c && "dd" === b && this._minWeekdaysParse[d].test(a)) return d;if (!c && this._weekdaysParse[d].test(a)) return d;
	    }
	  }function gc(a) {
	    if (!this.isValid()) return null != a ? this : NaN;var b = this._isUTC ? this._d.getUTCDay() : this._d.getDay();return null != a ? (a = ac(a, this.localeData()), this.add(a - b, "d")) : b;
	  }function hc(a) {
	    if (!this.isValid()) return null != a ? this : NaN;var b = (this.day() + 7 - this.localeData()._week.dow) % 7;return null == a ? b : this.add(a - b, "d");
	  }function ic(a) {
	    return this.isValid() ? null == a ? this.day() || 7 : this.day(this.day() % 7 ? a : a - 7) : null != a ? this : NaN;
	  }function jc(a) {
	    return this._weekdaysParseExact ? (f(this, "_weekdaysRegex") || mc.call(this), a ? this._weekdaysStrictRegex : this._weekdaysRegex) : this._weekdaysStrictRegex && a ? this._weekdaysStrictRegex : this._weekdaysRegex;
	  }function kc(a) {
	    return this._weekdaysParseExact ? (f(this, "_weekdaysRegex") || mc.call(this), a ? this._weekdaysShortStrictRegex : this._weekdaysShortRegex) : this._weekdaysShortStrictRegex && a ? this._weekdaysShortStrictRegex : this._weekdaysShortRegex;
	  }function lc(a) {
	    return this._weekdaysParseExact ? (f(this, "_weekdaysRegex") || mc.call(this), a ? this._weekdaysMinStrictRegex : this._weekdaysMinRegex) : this._weekdaysMinStrictRegex && a ? this._weekdaysMinStrictRegex : this._weekdaysMinRegex;
	  }function mc() {
	    function a(a, b) {
	      return b.length - a.length;
	    }var b,
	        c,
	        d,
	        e,
	        f,
	        g = [],
	        i = [],
	        j = [],
	        k = [];for (b = 0; 7 > b; b++) {
	      c = h([2e3, 1]).day(b), d = this.weekdaysMin(c, ""), e = this.weekdaysShort(c, ""), f = this.weekdays(c, ""), g.push(d), i.push(e), j.push(f), k.push(d), k.push(e), k.push(f);
	    }for (g.sort(a), i.sort(a), j.sort(a), k.sort(a), b = 0; 7 > b; b++) {
	      i[b] = Z(i[b]), j[b] = Z(j[b]), k[b] = Z(k[b]);
	    }this._weekdaysRegex = new RegExp("^(" + k.join("|") + ")", "i"), this._weekdaysShortRegex = this._weekdaysRegex, this._weekdaysMinRegex = this._weekdaysRegex, this._weekdaysStrictRegex = new RegExp("^(" + j.join("|") + ")", "i"), this._weekdaysShortStrictRegex = new RegExp("^(" + i.join("|") + ")", "i"), this._weekdaysMinStrictRegex = new RegExp("^(" + g.join("|") + ")", "i");
	  }function nc(a) {
	    var b = Math.round((this.clone().startOf("day") - this.clone().startOf("year")) / 864e5) + 1;return null == a ? b : this.add(a - b, "d");
	  }function oc() {
	    return this.hours() % 12 || 12;
	  }function pc() {
	    return this.hours() || 24;
	  }function qc(a, b) {
	    R(a, 0, 0, function () {
	      return this.localeData().meridiem(this.hours(), this.minutes(), b);
	    });
	  }function rc(a, b) {
	    return b._meridiemParse;
	  }function sc(a) {
	    return "p" === (a + "").toLowerCase().charAt(0);
	  }function tc(a, b, c) {
	    return a > 11 ? c ? "pm" : "PM" : c ? "am" : "AM";
	  }function uc(a, b) {
	    b[Sd] = r(1e3 * ("0." + a));
	  }function vc() {
	    return this._isUTC ? "UTC" : "";
	  }function wc() {
	    return this._isUTC ? "Coordinated Universal Time" : "";
	  }function xc(a) {
	    return Ka(1e3 * a);
	  }function yc() {
	    return Ka.apply(null, arguments).parseZone();
	  }function zc(a, b, c) {
	    var d = this._calendar[a];return w(d) ? d.call(b, c) : d;
	  }function Ac(a) {
	    var b = this._longDateFormat[a],
	        c = this._longDateFormat[a.toUpperCase()];return b || !c ? b : (this._longDateFormat[a] = c.replace(/MMMM|MM|DD|dddd/g, function (a) {
	      return a.slice(1);
	    }), this._longDateFormat[a]);
	  }function Bc() {
	    return this._invalidDate;
	  }function Cc(a) {
	    return this._ordinal.replace("%d", a);
	  }function Dc(a) {
	    return a;
	  }function Ec(a, b, c, d) {
	    var e = this._relativeTime[c];return w(e) ? e(a, b, c, d) : e.replace(/%d/i, a);
	  }function Fc(a, b) {
	    var c = this._relativeTime[a > 0 ? "future" : "past"];return w(c) ? c(b) : c.replace(/%s/i, b);
	  }function Gc(a, b, c, d) {
	    var e = H(),
	        f = h().set(d, b);return e[c](f, a);
	  }function Hc(a, b, c) {
	    if ("number" == typeof a && (b = a, a = void 0), a = a || "", null != b) return Gc(a, b, c, "month");var d,
	        e = [];for (d = 0; 12 > d; d++) {
	      e[d] = Gc(a, d, c, "month");
	    }return e;
	  }function Ic(a, b, c, d) {
	    "boolean" == typeof a ? ("number" == typeof b && (c = b, b = void 0), b = b || "") : (b = a, c = b, a = !1, "number" == typeof b && (c = b, b = void 0), b = b || "");var e = H(),
	        f = a ? e._week.dow : 0;if (null != c) return Gc(b, (c + f) % 7, d, "day");var g,
	        h = [];for (g = 0; 7 > g; g++) {
	      h[g] = Gc(b, (g + f) % 7, d, "day");
	    }return h;
	  }function Jc(a, b) {
	    return Hc(a, b, "months");
	  }function Kc(a, b) {
	    return Hc(a, b, "monthsShort");
	  }function Lc(a, b, c) {
	    return Ic(a, b, c, "weekdays");
	  }function Mc(a, b, c) {
	    return Ic(a, b, c, "weekdaysShort");
	  }function Nc(a, b, c) {
	    return Ic(a, b, c, "weekdaysMin");
	  }function Oc() {
	    var a = this._data;return this._milliseconds = Le(this._milliseconds), this._days = Le(this._days), this._months = Le(this._months), a.milliseconds = Le(a.milliseconds), a.seconds = Le(a.seconds), a.minutes = Le(a.minutes), a.hours = Le(a.hours), a.months = Le(a.months), a.years = Le(a.years), this;
	  }function Pc(a, b, c, d) {
	    var e = db(b, c);return a._milliseconds += d * e._milliseconds, a._days += d * e._days, a._months += d * e._months, a._bubble();
	  }function Qc(a, b) {
	    return Pc(this, a, b, 1);
	  }function Rc(a, b) {
	    return Pc(this, a, b, -1);
	  }function Sc(a) {
	    return 0 > a ? Math.floor(a) : Math.ceil(a);
	  }function Tc() {
	    var a,
	        b,
	        c,
	        d,
	        e,
	        f = this._milliseconds,
	        g = this._days,
	        h = this._months,
	        i = this._data;return f >= 0 && g >= 0 && h >= 0 || 0 >= f && 0 >= g && 0 >= h || (f += 864e5 * Sc(Vc(h) + g), g = 0, h = 0), i.milliseconds = f % 1e3, a = q(f / 1e3), i.seconds = a % 60, b = q(a / 60), i.minutes = b % 60, c = q(b / 60), i.hours = c % 24, g += q(c / 24), e = q(Uc(g)), h += e, g -= Sc(Vc(e)), d = q(h / 12), h %= 12, i.days = g, i.months = h, i.years = d, this;
	  }function Uc(a) {
	    return 4800 * a / 146097;
	  }function Vc(a) {
	    return 146097 * a / 4800;
	  }function Wc(a) {
	    var b,
	        c,
	        d = this._milliseconds;if (a = K(a), "month" === a || "year" === a) return b = this._days + d / 864e5, c = this._months + Uc(b), "month" === a ? c : c / 12;switch (b = this._days + Math.round(Vc(this._months)), a) {case "week":
	        return b / 7 + d / 6048e5;case "day":
	        return b + d / 864e5;case "hour":
	        return 24 * b + d / 36e5;case "minute":
	        return 1440 * b + d / 6e4;case "second":
	        return 86400 * b + d / 1e3;case "millisecond":
	        return Math.floor(864e5 * b) + d;default:
	        throw new Error("Unknown unit " + a);}
	  }function Xc() {
	    return this._milliseconds + 864e5 * this._days + this._months % 12 * 2592e6 + 31536e6 * r(this._months / 12);
	  }function Yc(a) {
	    return function () {
	      return this.as(a);
	    };
	  }function Zc(a) {
	    return a = K(a), this[a + "s"]();
	  }function $c(a) {
	    return function () {
	      return this._data[a];
	    };
	  }function _c() {
	    return q(this.days() / 7);
	  }function ad(a, b, c, d, e) {
	    return e.relativeTime(b || 1, !!c, a, d);
	  }function bd(a, b, c) {
	    var d = db(a).abs(),
	        e = _e(d.as("s")),
	        f = _e(d.as("m")),
	        g = _e(d.as("h")),
	        h = _e(d.as("d")),
	        i = _e(d.as("M")),
	        j = _e(d.as("y")),
	        k = e < af.s && ["s", e] || 1 >= f && ["m"] || f < af.m && ["mm", f] || 1 >= g && ["h"] || g < af.h && ["hh", g] || 1 >= h && ["d"] || h < af.d && ["dd", h] || 1 >= i && ["M"] || i < af.M && ["MM", i] || 1 >= j && ["y"] || ["yy", j];return k[2] = b, k[3] = +a > 0, k[4] = c, ad.apply(null, k);
	  }function cd(a, b) {
	    return void 0 === af[a] ? !1 : void 0 === b ? af[a] : (af[a] = b, !0);
	  }function dd(a) {
	    var b = this.localeData(),
	        c = bd(this, !a, b);return a && (c = b.pastFuture(+this, c)), b.postformat(c);
	  }function ed() {
	    var a,
	        b,
	        c,
	        d = bf(this._milliseconds) / 1e3,
	        e = bf(this._days),
	        f = bf(this._months);a = q(d / 60), b = q(a / 60), d %= 60, a %= 60, c = q(f / 12), f %= 12;var g = c,
	        h = f,
	        i = e,
	        j = b,
	        k = a,
	        l = d,
	        m = this.asSeconds();return m ? (0 > m ? "-" : "") + "P" + (g ? g + "Y" : "") + (h ? h + "M" : "") + (i ? i + "D" : "") + (j || k || l ? "T" : "") + (j ? j + "H" : "") + (k ? k + "M" : "") + (l ? l + "S" : "") : "P0D";
	  }var fd, gd;gd = Array.prototype.some ? Array.prototype.some : function (a) {
	    for (var b = Object(this), c = b.length >>> 0, d = 0; c > d; d++) {
	      if (d in b && a.call(this, b[d], d, b)) return !0;
	    }return !1;
	  };var hd = a.momentProperties = [],
	      id = !1,
	      jd = {};a.suppressDeprecationWarnings = !1, a.deprecationHandler = null;var kd;kd = Object.keys ? Object.keys : function (a) {
	    var b,
	        c = [];for (b in a) {
	      f(a, b) && c.push(b);
	    }return c;
	  };var ld,
	      md,
	      nd = {},
	      od = {},
	      pd = /(\[[^\[]*\])|(\\)?([Hh]mm(ss)?|Mo|MM?M?M?|Do|DDDo|DD?D?D?|ddd?d?|do?|w[o|w]?|W[o|W]?|Qo?|YYYYYY|YYYYY|YYYY|YY|gg(ggg?)?|GG(GGG?)?|e|E|a|A|hh?|HH?|kk?|mm?|ss?|S{1,9}|x|X|zz?|ZZ?|.)/g,
	      qd = /(\[[^\[]*\])|(\\)?(LTS|LT|LL?L?L?|l{1,4})/g,
	      rd = {},
	      sd = {},
	      td = /\d/,
	      ud = /\d\d/,
	      vd = /\d{3}/,
	      wd = /\d{4}/,
	      xd = /[+-]?\d{6}/,
	      yd = /\d\d?/,
	      zd = /\d\d\d\d?/,
	      Ad = /\d\d\d\d\d\d?/,
	      Bd = /\d{1,3}/,
	      Cd = /\d{1,4}/,
	      Dd = /[+-]?\d{1,6}/,
	      Ed = /\d+/,
	      Fd = /[+-]?\d+/,
	      Gd = /Z|[+-]\d\d:?\d\d/gi,
	      Hd = /Z|[+-]\d\d(?::?\d\d)?/gi,
	      Id = /[+-]?\d+(\.\d{1,3})?/,
	      Jd = /[0-9]*['a-z\u00A0-\u05FF\u0700-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]+|[\u0600-\u06FF\/]+(\s*?[\u0600-\u06FF]+){1,2}/i,
	      Kd = {},
	      Ld = {},
	      Md = 0,
	      Nd = 1,
	      Od = 2,
	      Pd = 3,
	      Qd = 4,
	      Rd = 5,
	      Sd = 6,
	      Td = 7,
	      Ud = 8;md = Array.prototype.indexOf ? Array.prototype.indexOf : function (a) {
	    var b;for (b = 0; b < this.length; ++b) {
	      if (this[b] === a) return b;
	    }return -1;
	  }, R("M", ["MM", 2], "Mo", function () {
	    return this.month() + 1;
	  }), R("MMM", 0, 0, function (a) {
	    return this.localeData().monthsShort(this, a);
	  }), R("MMMM", 0, 0, function (a) {
	    return this.localeData().months(this, a);
	  }), J("month", "M"), W("M", yd), W("MM", yd, ud), W("MMM", function (a, b) {
	    return b.monthsShortRegex(a);
	  }), W("MMMM", function (a, b) {
	    return b.monthsRegex(a);
	  }), $(["M", "MM"], function (a, b) {
	    b[Nd] = r(a) - 1;
	  }), $(["MMM", "MMMM"], function (a, b, c, d) {
	    var e = c._locale.monthsParse(a, d, c._strict);null != e ? b[Nd] = e : j(c).invalidMonth = a;
	  });var Vd = /D[oD]?(\[[^\[\]]*\]|\s+)+MMMM?/,
	      Wd = "January_February_March_April_May_June_July_August_September_October_November_December".split("_"),
	      Xd = "Jan_Feb_Mar_Apr_May_Jun_Jul_Aug_Sep_Oct_Nov_Dec".split("_"),
	      Yd = Jd,
	      Zd = Jd,
	      $d = /^\s*((?:[+-]\d{6}|\d{4})-(?:\d\d-\d\d|W\d\d-\d|W\d\d|\d\d\d|\d\d))(?:(T| )(\d\d(?::\d\d(?::\d\d(?:[.,]\d+)?)?)?)([\+\-]\d\d(?::?\d\d)?|\s*Z)?)?/,
	      _d = /^\s*((?:[+-]\d{6}|\d{4})(?:\d\d\d\d|W\d\d\d|W\d\d|\d\d\d|\d\d))(?:(T| )(\d\d(?:\d\d(?:\d\d(?:[.,]\d+)?)?)?)([\+\-]\d\d(?::?\d\d)?|\s*Z)?)?/,
	      ae = /Z|[+-]\d\d(?::?\d\d)?/,
	      be = [["YYYYYY-MM-DD", /[+-]\d{6}-\d\d-\d\d/], ["YYYY-MM-DD", /\d{4}-\d\d-\d\d/], ["GGGG-[W]WW-E", /\d{4}-W\d\d-\d/], ["GGGG-[W]WW", /\d{4}-W\d\d/, !1], ["YYYY-DDD", /\d{4}-\d{3}/], ["YYYY-MM", /\d{4}-\d\d/, !1], ["YYYYYYMMDD", /[+-]\d{10}/], ["YYYYMMDD", /\d{8}/], ["GGGG[W]WWE", /\d{4}W\d{3}/], ["GGGG[W]WW", /\d{4}W\d{2}/, !1], ["YYYYDDD", /\d{7}/]],
	      ce = [["HH:mm:ss.SSSS", /\d\d:\d\d:\d\d\.\d+/], ["HH:mm:ss,SSSS", /\d\d:\d\d:\d\d,\d+/], ["HH:mm:ss", /\d\d:\d\d:\d\d/], ["HH:mm", /\d\d:\d\d/], ["HHmmss.SSSS", /\d\d\d\d\d\d\.\d+/], ["HHmmss,SSSS", /\d\d\d\d\d\d,\d+/], ["HHmmss", /\d\d\d\d\d\d/], ["HHmm", /\d\d\d\d/], ["HH", /\d\d/]],
	      de = /^\/?Date\((\-?\d+)/i;a.createFromInputFallback = u("moment construction falls back to js Date. This is discouraged and will be removed in upcoming major release. Please refer to https://github.com/moment/moment/issues/1407 for more info.", function (a) {
	    a._d = new Date(a._i + (a._useUTC ? " UTC" : ""));
	  }), R("Y", 0, 0, function () {
	    var a = this.year();return 9999 >= a ? "" + a : "+" + a;
	  }), R(0, ["YY", 2], 0, function () {
	    return this.year() % 100;
	  }), R(0, ["YYYY", 4], 0, "year"), R(0, ["YYYYY", 5], 0, "year"), R(0, ["YYYYYY", 6, !0], 0, "year"), J("year", "y"), W("Y", Fd), W("YY", yd, ud), W("YYYY", Cd, wd), W("YYYYY", Dd, xd), W("YYYYYY", Dd, xd), $(["YYYYY", "YYYYYY"], Md), $("YYYY", function (b, c) {
	    c[Md] = 2 === b.length ? a.parseTwoDigitYear(b) : r(b);
	  }), $("YY", function (b, c) {
	    c[Md] = a.parseTwoDigitYear(b);
	  }), $("Y", function (a, b) {
	    b[Md] = parseInt(a, 10);
	  }), a.parseTwoDigitYear = function (a) {
	    return r(a) + (r(a) > 68 ? 1900 : 2e3);
	  };var ee = M("FullYear", !0);a.ISO_8601 = function () {};var fe = u("moment().min is deprecated, use moment.max instead. https://github.com/moment/moment/issues/1548", function () {
	    var a = Ka.apply(null, arguments);return this.isValid() && a.isValid() ? this > a ? this : a : l();
	  }),
	      ge = u("moment().max is deprecated, use moment.min instead. https://github.com/moment/moment/issues/1548", function () {
	    var a = Ka.apply(null, arguments);return this.isValid() && a.isValid() ? a > this ? this : a : l();
	  }),
	      he = function he() {
	    return Date.now ? Date.now() : +new Date();
	  };Qa("Z", ":"), Qa("ZZ", ""), W("Z", Hd), W("ZZ", Hd), $(["Z", "ZZ"], function (a, b, c) {
	    c._useUTC = !0, c._tzm = Ra(Hd, a);
	  });var ie = /([\+\-]|\d\d)/gi;a.updateOffset = function () {};var je = /^(\-)?(?:(\d*)[. ])?(\d+)\:(\d+)(?:\:(\d+)\.?(\d{3})?\d*)?$/,
	      ke = /^(-)?P(?:(-?[0-9,.]*)Y)?(?:(-?[0-9,.]*)M)?(?:(-?[0-9,.]*)W)?(?:(-?[0-9,.]*)D)?(?:T(?:(-?[0-9,.]*)H)?(?:(-?[0-9,.]*)M)?(?:(-?[0-9,.]*)S)?)?$/;db.fn = Oa.prototype;var le = ib(1, "add"),
	      me = ib(-1, "subtract");a.defaultFormat = "YYYY-MM-DDTHH:mm:ssZ", a.defaultFormatUtc = "YYYY-MM-DDTHH:mm:ss[Z]";var ne = u("moment().lang() is deprecated. Instead, use moment().localeData() to get the language configuration. Use moment().locale() to change languages.", function (a) {
	    return void 0 === a ? this.localeData() : this.locale(a);
	  });R(0, ["gg", 2], 0, function () {
	    return this.weekYear() % 100;
	  }), R(0, ["GG", 2], 0, function () {
	    return this.isoWeekYear() % 100;
	  }), Pb("gggg", "weekYear"), Pb("ggggg", "weekYear"), Pb("GGGG", "isoWeekYear"), Pb("GGGGG", "isoWeekYear"), J("weekYear", "gg"), J("isoWeekYear", "GG"), W("G", Fd), W("g", Fd), W("GG", yd, ud), W("gg", yd, ud), W("GGGG", Cd, wd), W("gggg", Cd, wd), W("GGGGG", Dd, xd), W("ggggg", Dd, xd), _(["gggg", "ggggg", "GGGG", "GGGGG"], function (a, b, c, d) {
	    b[d.substr(0, 2)] = r(a);
	  }), _(["gg", "GG"], function (b, c, d, e) {
	    c[e] = a.parseTwoDigitYear(b);
	  }), R("Q", 0, "Qo", "quarter"), J("quarter", "Q"), W("Q", td), $("Q", function (a, b) {
	    b[Nd] = 3 * (r(a) - 1);
	  }), R("w", ["ww", 2], "wo", "week"), R("W", ["WW", 2], "Wo", "isoWeek"), J("week", "w"), J("isoWeek", "W"), W("w", yd), W("ww", yd, ud), W("W", yd), W("WW", yd, ud), _(["w", "ww", "W", "WW"], function (a, b, c, d) {
	    b[d.substr(0, 1)] = r(a);
	  });var oe = { dow: 0, doy: 6 };R("D", ["DD", 2], "Do", "date"), J("date", "D"), W("D", yd), W("DD", yd, ud), W("Do", function (a, b) {
	    return a ? b._ordinalParse : b._ordinalParseLenient;
	  }), $(["D", "DD"], Od), $("Do", function (a, b) {
	    b[Od] = r(a.match(yd)[0], 10);
	  });var pe = M("Date", !0);R("d", 0, "do", "day"), R("dd", 0, 0, function (a) {
	    return this.localeData().weekdaysMin(this, a);
	  }), R("ddd", 0, 0, function (a) {
	    return this.localeData().weekdaysShort(this, a);
	  }), R("dddd", 0, 0, function (a) {
	    return this.localeData().weekdays(this, a);
	  }), R("e", 0, 0, "weekday"), R("E", 0, 0, "isoWeekday"), J("day", "d"), J("weekday", "e"), J("isoWeekday", "E"), W("d", yd), W("e", yd), W("E", yd), W("dd", function (a, b) {
	    return b.weekdaysMinRegex(a);
	  }), W("ddd", function (a, b) {
	    return b.weekdaysShortRegex(a);
	  }), W("dddd", function (a, b) {
	    return b.weekdaysRegex(a);
	  }), _(["dd", "ddd", "dddd"], function (a, b, c, d) {
	    var e = c._locale.weekdaysParse(a, d, c._strict);null != e ? b.d = e : j(c).invalidWeekday = a;
	  }), _(["d", "e", "E"], function (a, b, c, d) {
	    b[d] = r(a);
	  });var qe = "Sunday_Monday_Tuesday_Wednesday_Thursday_Friday_Saturday".split("_"),
	      re = "Sun_Mon_Tue_Wed_Thu_Fri_Sat".split("_"),
	      se = "Su_Mo_Tu_We_Th_Fr_Sa".split("_"),
	      te = Jd,
	      ue = Jd,
	      ve = Jd;R("DDD", ["DDDD", 3], "DDDo", "dayOfYear"), J("dayOfYear", "DDD"), W("DDD", Bd), W("DDDD", vd), $(["DDD", "DDDD"], function (a, b, c) {
	    c._dayOfYear = r(a);
	  }), R("H", ["HH", 2], 0, "hour"), R("h", ["hh", 2], 0, oc), R("k", ["kk", 2], 0, pc), R("hmm", 0, 0, function () {
	    return "" + oc.apply(this) + Q(this.minutes(), 2);
	  }), R("hmmss", 0, 0, function () {
	    return "" + oc.apply(this) + Q(this.minutes(), 2) + Q(this.seconds(), 2);
	  }), R("Hmm", 0, 0, function () {
	    return "" + this.hours() + Q(this.minutes(), 2);
	  }), R("Hmmss", 0, 0, function () {
	    return "" + this.hours() + Q(this.minutes(), 2) + Q(this.seconds(), 2);
	  }), qc("a", !0), qc("A", !1), J("hour", "h"), W("a", rc), W("A", rc), W("H", yd), W("h", yd), W("HH", yd, ud), W("hh", yd, ud), W("hmm", zd), W("hmmss", Ad), W("Hmm", zd), W("Hmmss", Ad), $(["H", "HH"], Pd), $(["a", "A"], function (a, b, c) {
	    c._isPm = c._locale.isPM(a), c._meridiem = a;
	  }), $(["h", "hh"], function (a, b, c) {
	    b[Pd] = r(a), j(c).bigHour = !0;
	  }), $("hmm", function (a, b, c) {
	    var d = a.length - 2;b[Pd] = r(a.substr(0, d)), b[Qd] = r(a.substr(d)), j(c).bigHour = !0;
	  }), $("hmmss", function (a, b, c) {
	    var d = a.length - 4,
	        e = a.length - 2;b[Pd] = r(a.substr(0, d)), b[Qd] = r(a.substr(d, 2)), b[Rd] = r(a.substr(e)), j(c).bigHour = !0;
	  }), $("Hmm", function (a, b, c) {
	    var d = a.length - 2;b[Pd] = r(a.substr(0, d)), b[Qd] = r(a.substr(d));
	  }), $("Hmmss", function (a, b, c) {
	    var d = a.length - 4,
	        e = a.length - 2;b[Pd] = r(a.substr(0, d)), b[Qd] = r(a.substr(d, 2)), b[Rd] = r(a.substr(e));
	  });var we = /[ap]\.?m?\.?/i,
	      xe = M("Hours", !0);R("m", ["mm", 2], 0, "minute"), J("minute", "m"), W("m", yd), W("mm", yd, ud), $(["m", "mm"], Qd);var ye = M("Minutes", !1);R("s", ["ss", 2], 0, "second"), J("second", "s"), W("s", yd), W("ss", yd, ud), $(["s", "ss"], Rd);var ze = M("Seconds", !1);R("S", 0, 0, function () {
	    return ~~(this.millisecond() / 100);
	  }), R(0, ["SS", 2], 0, function () {
	    return ~~(this.millisecond() / 10);
	  }), R(0, ["SSS", 3], 0, "millisecond"), R(0, ["SSSS", 4], 0, function () {
	    return 10 * this.millisecond();
	  }), R(0, ["SSSSS", 5], 0, function () {
	    return 100 * this.millisecond();
	  }), R(0, ["SSSSSS", 6], 0, function () {
	    return 1e3 * this.millisecond();
	  }), R(0, ["SSSSSSS", 7], 0, function () {
	    return 1e4 * this.millisecond();
	  }), R(0, ["SSSSSSSS", 8], 0, function () {
	    return 1e5 * this.millisecond();
	  }), R(0, ["SSSSSSSSS", 9], 0, function () {
	    return 1e6 * this.millisecond();
	  }), J("millisecond", "ms"), W("S", Bd, td), W("SS", Bd, ud), W("SSS", Bd, vd);var Ae;for (Ae = "SSSS"; Ae.length <= 9; Ae += "S") {
	    W(Ae, Ed);
	  }for (Ae = "S"; Ae.length <= 9; Ae += "S") {
	    $(Ae, uc);
	  }var Be = M("Milliseconds", !1);R("z", 0, 0, "zoneAbbr"), R("zz", 0, 0, "zoneName");var Ce = o.prototype;Ce.add = le, Ce.calendar = kb, Ce.clone = lb, Ce.diff = sb, Ce.endOf = Eb, Ce.format = wb, Ce.from = xb, Ce.fromNow = yb, Ce.to = zb, Ce.toNow = Ab, Ce.get = P, Ce.invalidAt = Nb, Ce.isAfter = mb, Ce.isBefore = nb, Ce.isBetween = ob, Ce.isSame = pb, Ce.isSameOrAfter = qb, Ce.isSameOrBefore = rb, Ce.isValid = Lb, Ce.lang = ne, Ce.locale = Bb, Ce.localeData = Cb, Ce.max = ge, Ce.min = fe, Ce.parsingFlags = Mb, Ce.set = P, Ce.startOf = Db, Ce.subtract = me, Ce.toArray = Ib, Ce.toObject = Jb, Ce.toDate = Hb, Ce.toISOString = vb, Ce.toJSON = Kb, Ce.toString = ub, Ce.unix = Gb, Ce.valueOf = Fb, Ce.creationData = Ob, Ce.year = ee, Ce.isLeapYear = ta, Ce.weekYear = Qb, Ce.isoWeekYear = Rb, Ce.quarter = Ce.quarters = Wb, Ce.month = ha, Ce.daysInMonth = ia, Ce.week = Ce.weeks = $b, Ce.isoWeek = Ce.isoWeeks = _b, Ce.weeksInYear = Tb, Ce.isoWeeksInYear = Sb, Ce.date = pe, Ce.day = Ce.days = gc, Ce.weekday = hc, Ce.isoWeekday = ic, Ce.dayOfYear = nc, Ce.hour = Ce.hours = xe, Ce.minute = Ce.minutes = ye, Ce.second = Ce.seconds = ze, Ce.millisecond = Ce.milliseconds = Be, Ce.utcOffset = Ua, Ce.utc = Wa, Ce.local = Xa, Ce.parseZone = Ya, Ce.hasAlignedHourOffset = Za, Ce.isDST = $a, Ce.isDSTShifted = _a, Ce.isLocal = ab, Ce.isUtcOffset = bb, Ce.isUtc = cb, Ce.isUTC = cb, Ce.zoneAbbr = vc, Ce.zoneName = wc, Ce.dates = u("dates accessor is deprecated. Use date instead.", pe), Ce.months = u("months accessor is deprecated. Use month instead", ha), Ce.years = u("years accessor is deprecated. Use year instead", ee), Ce.zone = u("moment().zone is deprecated, use moment().utcOffset instead. https://github.com/moment/moment/issues/1779", Va);var De = Ce,
	      Ee = { sameDay: "[Today at] LT", nextDay: "[Tomorrow at] LT", nextWeek: "dddd [at] LT", lastDay: "[Yesterday at] LT", lastWeek: "[Last] dddd [at] LT", sameElse: "L" },
	      Fe = { LTS: "h:mm:ss A", LT: "h:mm A", L: "MM/DD/YYYY", LL: "MMMM D, YYYY", LLL: "MMMM D, YYYY h:mm A", LLLL: "dddd, MMMM D, YYYY h:mm A" },
	      Ge = "Invalid date",
	      He = "%d",
	      Ie = /\d{1,2}/,
	      Je = { future: "in %s", past: "%s ago", s: "a few seconds", m: "a minute", mm: "%d minutes", h: "an hour", hh: "%d hours", d: "a day", dd: "%d days", M: "a month", MM: "%d months", y: "a year", yy: "%d years" },
	      Ke = A.prototype;Ke._calendar = Ee, Ke.calendar = zc, Ke._longDateFormat = Fe, Ke.longDateFormat = Ac, Ke._invalidDate = Ge, Ke.invalidDate = Bc, Ke._ordinal = He, Ke.ordinal = Cc, Ke._ordinalParse = Ie, Ke.preparse = Dc, Ke.postformat = Dc, Ke._relativeTime = Je, Ke.relativeTime = Ec, Ke.pastFuture = Fc, Ke.set = y, Ke.months = ca, Ke._months = Wd, Ke.monthsShort = da, Ke._monthsShort = Xd, Ke.monthsParse = fa, Ke._monthsRegex = Zd, Ke.monthsRegex = ka, Ke._monthsShortRegex = Yd, Ke.monthsShortRegex = ja, Ke.week = Xb, Ke._week = oe, Ke.firstDayOfYear = Zb, Ke.firstDayOfWeek = Yb, Ke.weekdays = bc, Ke._weekdays = qe, Ke.weekdaysMin = dc, Ke._weekdaysMin = se, Ke.weekdaysShort = cc, Ke._weekdaysShort = re, Ke.weekdaysParse = fc, Ke._weekdaysRegex = te, Ke.weekdaysRegex = jc, Ke._weekdaysShortRegex = ue, Ke.weekdaysShortRegex = kc, Ke._weekdaysMinRegex = ve, Ke.weekdaysMinRegex = lc, Ke.isPM = sc, Ke._meridiemParse = we, Ke.meridiem = tc, E("en", { ordinalParse: /\d{1,2}(th|st|nd|rd)/, ordinal: function ordinal(a) {
	      var b = a % 10,
	          c = 1 === r(a % 100 / 10) ? "th" : 1 === b ? "st" : 2 === b ? "nd" : 3 === b ? "rd" : "th";return a + c;
	    } }), a.lang = u("moment.lang is deprecated. Use moment.locale instead.", E), a.langData = u("moment.langData is deprecated. Use moment.localeData instead.", H);var Le = Math.abs,
	      Me = Yc("ms"),
	      Ne = Yc("s"),
	      Oe = Yc("m"),
	      Pe = Yc("h"),
	      Qe = Yc("d"),
	      Re = Yc("w"),
	      Se = Yc("M"),
	      Te = Yc("y"),
	      Ue = $c("milliseconds"),
	      Ve = $c("seconds"),
	      We = $c("minutes"),
	      Xe = $c("hours"),
	      Ye = $c("days"),
	      Ze = $c("months"),
	      $e = $c("years"),
	      _e = Math.round,
	      af = { s: 45, m: 45, h: 22, d: 26, M: 11 },
	      bf = Math.abs,
	      cf = Oa.prototype;cf.abs = Oc, cf.add = Qc, cf.subtract = Rc, cf.as = Wc, cf.asMilliseconds = Me, cf.asSeconds = Ne, cf.asMinutes = Oe, cf.asHours = Pe, cf.asDays = Qe, cf.asWeeks = Re, cf.asMonths = Se, cf.asYears = Te, cf.valueOf = Xc, cf._bubble = Tc, cf.get = Zc, cf.milliseconds = Ue, cf.seconds = Ve, cf.minutes = We, cf.hours = Xe, cf.days = Ye, cf.weeks = _c, cf.months = Ze, cf.years = $e, cf.humanize = dd, cf.toISOString = ed, cf.toString = ed, cf.toJSON = ed, cf.locale = Bb, cf.localeData = Cb, cf.toIsoString = u("toIsoString() is deprecated. Please use toISOString() instead (notice the capitals)", ed), cf.lang = ne, R("X", 0, 0, "unix"), R("x", 0, 0, "valueOf"), W("x", Fd), W("X", Id), $("X", function (a, b, c) {
	    c._d = new Date(1e3 * parseFloat(a, 10));
	  }), $("x", function (a, b, c) {
	    c._d = new Date(r(a));
	  }), a.version = "2.13.0", b(Ka), a.fn = De, a.min = Ma, a.max = Na, a.now = he, a.utc = h, a.unix = xc, a.months = Jc, a.isDate = d, a.locale = E, a.invalid = l, a.duration = db, a.isMoment = p, a.weekdays = Lc, a.parseZone = yc, a.localeData = H, a.isDuration = Pa, a.monthsShort = Kc, a.weekdaysMin = Nc, a.defineLocale = F, a.updateLocale = G, a.locales = I, a.weekdaysShort = Mc, a.normalizeUnits = K, a.relativeTimeThreshold = cd, a.prototype = De;var df = a;return df;
	});
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(9)(module)))

/***/ },
/* 9 */
/***/ function(module, exports) {

	module.exports = function(module) {
		if(!module.webpackPolyfill) {
			module.deprecate = function() {};
			module.paths = [];
			// module.parent = undefined by default
			module.children = [];
			module.webpackPolyfill = 1;
		}
		return module;
	}


/***/ },
/* 10 */
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function($, c3) {"use strict";

	exports.__esModule = true;

	var _d = __webpack_require__(4);

	var d3 = _interopRequireWildcard(_d);

	function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

	function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

	// TODO: Also, used global c3, URLS, jQuery. Investigate how to import them explicitly

	var AssignmentsResults = function () {
	    function AssignmentsResults(id, options) {
	        var _this = this;

	        _classCallCheck(this, AssignmentsResults);

	        this.i18n = {
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

	        this.convertData = function (jsonData) {
	            console.log("performance ", jsonData);
	            var states = Array.from(_this.states, function (_ref) {
	                var k = _ref[0],
	                    v = _ref[1];
	                return v;
	            }),
	                titles = [],
	                rows = [states];

	            jsonData.forEach(function (assignment) {
	                titles.push(assignment.title);
	                var counters = states.reduce(function (a, b) {
	                    return a.set(b, 0);
	                }, new Map());
	                assignment.assigned_to.forEach(function (student) {
	                    var state = _this.states.get(student.state);
	                    counters.set(state, counters.get(state) + 1);
	                });
	                rows.push(Array.from(counters, function (_ref2) {
	                    var k = _ref2[0],
	                        v = _ref2[1];
	                    return v;
	                }));
	            });

	            _this.data = {
	                titles: titles, // assignment titles
	                rows: rows
	            };
	            console.debug("performance data", _this.data);
	            return _this.data;
	        };

	        this.render = function (data) {
	            if (!data.titles.length) {
	                $(_this.id).html(_this.i18n.ru.no_assignments);
	                return;
	            }

	            // Let's generate here, a lot of troubles with c3.load method right now
	            console.log(data);
	            _this.plot = c3.generate({
	                bindto: _this.id,
	                data: {
	                    type: _this.type,
	                    rows: data.rows
	                },
	                tooltip: {
	                    format: {
	                        title: function title(d) {
	                            return data.titles[d];
	                        }
	                    }
	                },
	                axis: {
	                    x: {
	                        tick: {
	                            format: function format(x) {
	                                return x + 1;
	                            }
	                        }
	                    }
	                },
	                grid: {
	                    y: {
	                        show: true
	                    }
	                },
	                color: {
	                    pattern: ['#7f7f7f', '#ffbb78', '#d62728', '#ff7f0e', '#2ca02c', '#9c27b0', '#c7c7c7', '#bcbd22', '#dbdb8d', '#17becf', '#9edae5']
	                }
	            });
	        };

	        this.id = id;
	        this.type = 'bar';
	        this.data = {};
	        this.plot = undefined;

	        // Order is unspecified for Object, but I believe browsers sort
	        // it in a proper way
	        this.states = Object.keys(this.i18n.ru.grades).reduce(function (m, k) {
	            return m.set(k, _this.i18n.ru.grades[k]);
	        }, new Map());

	        var promise = options.apiRequest || this.getStats(options.course_session_id);
	        promise.then(this.convertData).done(this.render);
	    }

	    AssignmentsResults.getStats = function getStats(course_session_id) {
	        var dataURL = URLS["api:stats_assignments"](course_session_id);
	        return $.getJSON(dataURL);
	    };

	    return AssignmentsResults;
	}();

	exports.default = AssignmentsResults;
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(1), __webpack_require__(3)))

/***/ },
/* 11 */
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function($, c3) {"use strict";

	exports.__esModule = true;

	var _d = __webpack_require__(4);

	var d3 = _interopRequireWildcard(_d);

	function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

	function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

	// TODO: Also, used global c3, URLS, jQuery. Investigate how to import them explicitly

	var AssignmentsScore = function () {
	    function AssignmentsScore(id, options) {
	        var _this = this;

	        _classCallCheck(this, AssignmentsScore);

	        this.i18n = {
	            lang: 'ru',
	            ru: {
	                no_assignments: "Заданий не найдено.",
	                lines: {
	                    pass: "Проходной балл",
	                    mean: "Средний балл"
	                }
	            }
	        };

	        this.convertData = function (jsonData) {
	            console.log(jsonData);
	            var titles = [],
	                rows = [[_this.i18n.ru.lines.pass, _this.i18n.ru.lines.mean]];

	            jsonData.forEach(function (assignment) {
	                titles.push(assignment.title);
	                var sum = 0,
	                    cnt = 0;
	                // Looks complicated to use Array.prototype.filter
	                assignment.assigned_to.forEach(function (student) {
	                    if (student.grade !== null) {
	                        sum += student.grade;
	                        cnt += 1;
	                    }
	                });
	                var mean = cnt === 0 ? 0 : (sum / cnt).toFixed(1);
	                rows.push([assignment.grade_min, mean]);
	            });

	            _this.data = {
	                titles: titles,
	                rows: rows
	            };
	            console.debug(_this.data);
	            return _this.data;
	        };

	        this.render = function (data) {
	            if (!data.titles.length) {
	                $(_this.id).html(_this.i18n.ru.no_assignments);
	                return;
	            }

	            // Let's generate here, a lot of troubles with c3.load method right now
	            console.log(data);
	            _this.plot = c3.generate({
	                bindto: _this.id,
	                data: {
	                    type: _this.type,
	                    rows: data.rows
	                },
	                tooltip: {
	                    format: {
	                        title: function title(d) {
	                            return data.titles[d];
	                        }
	                    }
	                },
	                axis: {
	                    x: {
	                        tick: {
	                            format: function format(x) {
	                                return x + 1;
	                            }
	                        }
	                    }
	                },
	                legend: {
	                    position: 'right'
	                },
	                grid: {
	                    y: {
	                        show: true
	                    }
	                }
	            });
	        };

	        this.id = id;
	        this.type = 'line';
	        this.data = {};
	        this.plot = undefined;

	        var promise = options.apiRequest || this.getStats(options.course_session_id);
	        promise.then(this.convertData).done(this.render);
	    }

	    AssignmentsScore.getStats = function getStats(course_session_id) {
	        var dataURL = URLS["api:stats_assignments"](course_session_id);
	        return $.getJSON(dataURL);
	    };

	    return AssignmentsScore;
	}();

	exports.default = AssignmentsScore;
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(1), __webpack_require__(3)))

/***/ },
/* 12 */
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function($, c3) {"use strict";

	exports.__esModule = true;

	var _d = __webpack_require__(4);

	var d3 = _interopRequireWildcard(_d);

	function _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }

	function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

	// TODO: Also, used global c3, URLS, jQuery. Investigate how to import them explicitly

	var EnrollmentsResults = function () {
	    function EnrollmentsResults(id, course_session_id) {
	        var _this = this;

	        _classCallCheck(this, EnrollmentsResults);

	        this.i18n = {
	            lang: 'ru',
	            ru: {
	                no_enrollments: "Студенты не найдены.",
	                grades: {
	                    not_graded: "Без оценки",
	                    unsatisfactory: "Незачет",
	                    pass: "Удовлетворительно",
	                    good: "Хорошо",
	                    excellent: "Отлично"
	                }
	            }
	        };

	        this.convertData = function (jsonData) {
	            var data = {};
	            jsonData.forEach(function (e) {
	                if (!(e.grade in data)) {
	                    data[e.grade] = 0;
	                }
	                data[e.grade] += 1;
	            });
	            _this.data = data;
	            var columns = [];
	            for (var key in data) {
	                console.log(_this.grades, key);
	                columns.push([_this.grades.get(key), data[key]]);
	            }
	            return columns;
	        };

	        this.render = function (data) {
	            if (!data.length) {
	                $(_this.id).html(_this.i18n.ru.no_enrollments);
	                return;
	            }

	            // Let's generate here, a lot of troubles with c3.load method right now
	            console.log(data);
	            _this.plot = c3.generate({
	                bindto: _this.id,
	                data: {
	                    type: _this.type,
	                    columns: data
	                },
	                tooltip: {
	                    format: {
	                        value: function value(_value, ratio, id) {
	                            if (_this.type == 'pie') {
	                                return _value + '&nbsp;чел.';
	                            } else {
	                                return _value;
	                            }
	                        }
	                    }
	                },
	                legend: {
	                    position: 'right'
	                },
	                grid: {
	                    y: {
	                        show: true
	                    }
	                }
	            });
	        };

	        this.id = id;
	        this.type = 'pie';
	        this.data = {};
	        this.plot = undefined;

	        this.grades = Object.keys(this.i18n.ru.grades).reduce(function (m, k) {
	            return m.set(k, _this.i18n.ru.grades[k]);
	        }, new Map());

	        this.loadStats(course_session_id).done(this.render);
	    }

	    EnrollmentsResults.prototype.loadStats = function loadStats(course_session_id) {
	        return this.getJSON(course_session_id).then(this.convertData);
	    };

	    EnrollmentsResults.prototype.getJSON = function getJSON(course_session_id) {
	        var dataURL = URLS["api:stats_enrollments"](course_session_id);
	        return $.getJSON(dataURL);
	    };

	    return EnrollmentsResults;
	}();

	exports.default = EnrollmentsResults;
	/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(1), __webpack_require__(3)))

/***/ },
/* 13 */
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function(global) {/**
	 * lodash (Custom Build) <https://lodash.com/>
	 * Build: `lodash modularize exports="npm" -o ./`
	 * Copyright jQuery Foundation and other contributors <https://jquery.org/>
	 * Released under MIT license <https://lodash.com/license>
	 * Based on Underscore.js 1.8.3 <http://underscorejs.org/LICENSE>
	 * Copyright Jeremy Ashkenas, DocumentCloud and Investigative Reporters & Editors
	 */
	var reInterpolate = __webpack_require__(14),
	    templateSettings = __webpack_require__(15);

	/** Used as references for various `Number` constants. */
	var INFINITY = 1 / 0,
	    MAX_SAFE_INTEGER = 9007199254740991;

	/** `Object#toString` result references. */
	var argsTag = '[object Arguments]',
	    errorTag = '[object Error]',
	    funcTag = '[object Function]',
	    genTag = '[object GeneratorFunction]',
	    symbolTag = '[object Symbol]';

	/** Used to match empty string literals in compiled template source. */
	var reEmptyStringLeading = /\b__p \+= '';/g,
	    reEmptyStringMiddle = /\b(__p \+=) '' \+/g,
	    reEmptyStringTrailing = /(__e\(.*?\)|\b__t\)) \+\n'';/g;

	/**
	 * Used to match
	 * [ES template delimiters](http://ecma-international.org/ecma-262/7.0/#sec-template-literal-lexical-components).
	 */
	var reEsTemplate = /\$\{([^\\}]*(?:\\.[^\\}]*)*)\}/g;

	/** Used to detect unsigned integer values. */
	var reIsUint = /^(?:0|[1-9]\d*)$/;

	/** Used to ensure capturing order of template delimiters. */
	var reNoMatch = /($^)/;

	/** Used to match unescaped characters in compiled string literals. */
	var reUnescapedString = /['\n\r\u2028\u2029\\]/g;

	/** Used to escape characters for inclusion in compiled string literals. */
	var stringEscapes = {
	  '\\': '\\',
	  "'": "'",
	  '\n': 'n',
	  '\r': 'r',
	  '\u2028': 'u2028',
	  '\u2029': 'u2029'
	};

	/** Detect free variable `global` from Node.js. */
	var freeGlobal = typeof global == 'object' && global && global.Object === Object && global;

	/** Detect free variable `self`. */
	var freeSelf = typeof self == 'object' && self && self.Object === Object && self;

	/** Used as a reference to the global object. */
	var root = freeGlobal || freeSelf || Function('return this')();

	/**
	 * A faster alternative to `Function#apply`, this function invokes `func`
	 * with the `this` binding of `thisArg` and the arguments of `args`.
	 *
	 * @private
	 * @param {Function} func The function to invoke.
	 * @param {*} thisArg The `this` binding of `func`.
	 * @param {Array} args The arguments to invoke `func` with.
	 * @returns {*} Returns the result of `func`.
	 */
	function apply(func, thisArg, args) {
	  switch (args.length) {
	    case 0: return func.call(thisArg);
	    case 1: return func.call(thisArg, args[0]);
	    case 2: return func.call(thisArg, args[0], args[1]);
	    case 3: return func.call(thisArg, args[0], args[1], args[2]);
	  }
	  return func.apply(thisArg, args);
	}

	/**
	 * A specialized version of `_.map` for arrays without support for iteratee
	 * shorthands.
	 *
	 * @private
	 * @param {Array} [array] The array to iterate over.
	 * @param {Function} iteratee The function invoked per iteration.
	 * @returns {Array} Returns the new mapped array.
	 */
	function arrayMap(array, iteratee) {
	  var index = -1,
	      length = array ? array.length : 0,
	      result = Array(length);

	  while (++index < length) {
	    result[index] = iteratee(array[index], index, array);
	  }
	  return result;
	}

	/**
	 * The base implementation of `_.times` without support for iteratee shorthands
	 * or max array length checks.
	 *
	 * @private
	 * @param {number} n The number of times to invoke `iteratee`.
	 * @param {Function} iteratee The function invoked per iteration.
	 * @returns {Array} Returns the array of results.
	 */
	function baseTimes(n, iteratee) {
	  var index = -1,
	      result = Array(n);

	  while (++index < n) {
	    result[index] = iteratee(index);
	  }
	  return result;
	}

	/**
	 * The base implementation of `_.values` and `_.valuesIn` which creates an
	 * array of `object` property values corresponding to the property names
	 * of `props`.
	 *
	 * @private
	 * @param {Object} object The object to query.
	 * @param {Array} props The property names to get values for.
	 * @returns {Object} Returns the array of property values.
	 */
	function baseValues(object, props) {
	  return arrayMap(props, function(key) {
	    return object[key];
	  });
	}

	/**
	 * Used by `_.template` to escape characters for inclusion in compiled string literals.
	 *
	 * @private
	 * @param {string} chr The matched character to escape.
	 * @returns {string} Returns the escaped character.
	 */
	function escapeStringChar(chr) {
	  return '\\' + stringEscapes[chr];
	}

	/**
	 * Creates a unary function that invokes `func` with its argument transformed.
	 *
	 * @private
	 * @param {Function} func The function to wrap.
	 * @param {Function} transform The argument transform.
	 * @returns {Function} Returns the new function.
	 */
	function overArg(func, transform) {
	  return function(arg) {
	    return func(transform(arg));
	  };
	}

	/** Used for built-in method references. */
	var objectProto = Object.prototype;

	/** Used to check objects for own properties. */
	var hasOwnProperty = objectProto.hasOwnProperty;

	/**
	 * Used to resolve the
	 * [`toStringTag`](http://ecma-international.org/ecma-262/7.0/#sec-object.prototype.tostring)
	 * of values.
	 */
	var objectToString = objectProto.toString;

	/** Built-in value references. */
	var Symbol = root.Symbol,
	    propertyIsEnumerable = objectProto.propertyIsEnumerable;

	/* Built-in method references for those with the same name as other `lodash` methods. */
	var nativeKeys = overArg(Object.keys, Object),
	    nativeMax = Math.max;

	/** Used to convert symbols to primitives and strings. */
	var symbolProto = Symbol ? Symbol.prototype : undefined,
	    symbolToString = symbolProto ? symbolProto.toString : undefined;

	/**
	 * Creates an array of the enumerable property names of the array-like `value`.
	 *
	 * @private
	 * @param {*} value The value to query.
	 * @param {boolean} inherited Specify returning inherited property names.
	 * @returns {Array} Returns the array of property names.
	 */
	function arrayLikeKeys(value, inherited) {
	  // Safari 8.1 makes `arguments.callee` enumerable in strict mode.
	  // Safari 9 makes `arguments.length` enumerable in strict mode.
	  var result = (isArray(value) || isArguments(value))
	    ? baseTimes(value.length, String)
	    : [];

	  var length = result.length,
	      skipIndexes = !!length;

	  for (var key in value) {
	    if ((inherited || hasOwnProperty.call(value, key)) &&
	        !(skipIndexes && (key == 'length' || isIndex(key, length)))) {
	      result.push(key);
	    }
	  }
	  return result;
	}

	/**
	 * Used by `_.defaults` to customize its `_.assignIn` use.
	 *
	 * @private
	 * @param {*} objValue The destination value.
	 * @param {*} srcValue The source value.
	 * @param {string} key The key of the property to assign.
	 * @param {Object} object The parent object of `objValue`.
	 * @returns {*} Returns the value to assign.
	 */
	function assignInDefaults(objValue, srcValue, key, object) {
	  if (objValue === undefined ||
	      (eq(objValue, objectProto[key]) && !hasOwnProperty.call(object, key))) {
	    return srcValue;
	  }
	  return objValue;
	}

	/**
	 * Assigns `value` to `key` of `object` if the existing value is not equivalent
	 * using [`SameValueZero`](http://ecma-international.org/ecma-262/7.0/#sec-samevaluezero)
	 * for equality comparisons.
	 *
	 * @private
	 * @param {Object} object The object to modify.
	 * @param {string} key The key of the property to assign.
	 * @param {*} value The value to assign.
	 */
	function assignValue(object, key, value) {
	  var objValue = object[key];
	  if (!(hasOwnProperty.call(object, key) && eq(objValue, value)) ||
	      (value === undefined && !(key in object))) {
	    object[key] = value;
	  }
	}

	/**
	 * The base implementation of `_.keys` which doesn't treat sparse arrays as dense.
	 *
	 * @private
	 * @param {Object} object The object to query.
	 * @returns {Array} Returns the array of property names.
	 */
	function baseKeys(object) {
	  if (!isPrototype(object)) {
	    return nativeKeys(object);
	  }
	  var result = [];
	  for (var key in Object(object)) {
	    if (hasOwnProperty.call(object, key) && key != 'constructor') {
	      result.push(key);
	    }
	  }
	  return result;
	}

	/**
	 * The base implementation of `_.keysIn` which doesn't treat sparse arrays as dense.
	 *
	 * @private
	 * @param {Object} object The object to query.
	 * @returns {Array} Returns the array of property names.
	 */
	function baseKeysIn(object) {
	  if (!isObject(object)) {
	    return nativeKeysIn(object);
	  }
	  var isProto = isPrototype(object),
	      result = [];

	  for (var key in object) {
	    if (!(key == 'constructor' && (isProto || !hasOwnProperty.call(object, key)))) {
	      result.push(key);
	    }
	  }
	  return result;
	}

	/**
	 * The base implementation of `_.rest` which doesn't validate or coerce arguments.
	 *
	 * @private
	 * @param {Function} func The function to apply a rest parameter to.
	 * @param {number} [start=func.length-1] The start position of the rest parameter.
	 * @returns {Function} Returns the new function.
	 */
	function baseRest(func, start) {
	  start = nativeMax(start === undefined ? (func.length - 1) : start, 0);
	  return function() {
	    var args = arguments,
	        index = -1,
	        length = nativeMax(args.length - start, 0),
	        array = Array(length);

	    while (++index < length) {
	      array[index] = args[start + index];
	    }
	    index = -1;
	    var otherArgs = Array(start + 1);
	    while (++index < start) {
	      otherArgs[index] = args[index];
	    }
	    otherArgs[start] = array;
	    return apply(func, this, otherArgs);
	  };
	}

	/**
	 * The base implementation of `_.toString` which doesn't convert nullish
	 * values to empty strings.
	 *
	 * @private
	 * @param {*} value The value to process.
	 * @returns {string} Returns the string.
	 */
	function baseToString(value) {
	  // Exit early for strings to avoid a performance hit in some environments.
	  if (typeof value == 'string') {
	    return value;
	  }
	  if (isSymbol(value)) {
	    return symbolToString ? symbolToString.call(value) : '';
	  }
	  var result = (value + '');
	  return (result == '0' && (1 / value) == -INFINITY) ? '-0' : result;
	}

	/**
	 * Copies properties of `source` to `object`.
	 *
	 * @private
	 * @param {Object} source The object to copy properties from.
	 * @param {Array} props The property identifiers to copy.
	 * @param {Object} [object={}] The object to copy properties to.
	 * @param {Function} [customizer] The function to customize copied values.
	 * @returns {Object} Returns `object`.
	 */
	function copyObject(source, props, object, customizer) {
	  object || (object = {});

	  var index = -1,
	      length = props.length;

	  while (++index < length) {
	    var key = props[index];

	    var newValue = customizer
	      ? customizer(object[key], source[key], key, object, source)
	      : undefined;

	    assignValue(object, key, newValue === undefined ? source[key] : newValue);
	  }
	  return object;
	}

	/**
	 * Creates a function like `_.assign`.
	 *
	 * @private
	 * @param {Function} assigner The function to assign values.
	 * @returns {Function} Returns the new assigner function.
	 */
	function createAssigner(assigner) {
	  return baseRest(function(object, sources) {
	    var index = -1,
	        length = sources.length,
	        customizer = length > 1 ? sources[length - 1] : undefined,
	        guard = length > 2 ? sources[2] : undefined;

	    customizer = (assigner.length > 3 && typeof customizer == 'function')
	      ? (length--, customizer)
	      : undefined;

	    if (guard && isIterateeCall(sources[0], sources[1], guard)) {
	      customizer = length < 3 ? undefined : customizer;
	      length = 1;
	    }
	    object = Object(object);
	    while (++index < length) {
	      var source = sources[index];
	      if (source) {
	        assigner(object, source, index, customizer);
	      }
	    }
	    return object;
	  });
	}

	/**
	 * Checks if `value` is a valid array-like index.
	 *
	 * @private
	 * @param {*} value The value to check.
	 * @param {number} [length=MAX_SAFE_INTEGER] The upper bounds of a valid index.
	 * @returns {boolean} Returns `true` if `value` is a valid index, else `false`.
	 */
	function isIndex(value, length) {
	  length = length == null ? MAX_SAFE_INTEGER : length;
	  return !!length &&
	    (typeof value == 'number' || reIsUint.test(value)) &&
	    (value > -1 && value % 1 == 0 && value < length);
	}

	/**
	 * Checks if the given arguments are from an iteratee call.
	 *
	 * @private
	 * @param {*} value The potential iteratee value argument.
	 * @param {*} index The potential iteratee index or key argument.
	 * @param {*} object The potential iteratee object argument.
	 * @returns {boolean} Returns `true` if the arguments are from an iteratee call,
	 *  else `false`.
	 */
	function isIterateeCall(value, index, object) {
	  if (!isObject(object)) {
	    return false;
	  }
	  var type = typeof index;
	  if (type == 'number'
	        ? (isArrayLike(object) && isIndex(index, object.length))
	        : (type == 'string' && index in object)
	      ) {
	    return eq(object[index], value);
	  }
	  return false;
	}

	/**
	 * Checks if `value` is likely a prototype object.
	 *
	 * @private
	 * @param {*} value The value to check.
	 * @returns {boolean} Returns `true` if `value` is a prototype, else `false`.
	 */
	function isPrototype(value) {
	  var Ctor = value && value.constructor,
	      proto = (typeof Ctor == 'function' && Ctor.prototype) || objectProto;

	  return value === proto;
	}

	/**
	 * This function is like
	 * [`Object.keys`](http://ecma-international.org/ecma-262/7.0/#sec-object.keys)
	 * except that it includes inherited enumerable properties.
	 *
	 * @private
	 * @param {Object} object The object to query.
	 * @returns {Array} Returns the array of property names.
	 */
	function nativeKeysIn(object) {
	  var result = [];
	  if (object != null) {
	    for (var key in Object(object)) {
	      result.push(key);
	    }
	  }
	  return result;
	}

	/**
	 * Performs a
	 * [`SameValueZero`](http://ecma-international.org/ecma-262/7.0/#sec-samevaluezero)
	 * comparison between two values to determine if they are equivalent.
	 *
	 * @static
	 * @memberOf _
	 * @since 4.0.0
	 * @category Lang
	 * @param {*} value The value to compare.
	 * @param {*} other The other value to compare.
	 * @returns {boolean} Returns `true` if the values are equivalent, else `false`.
	 * @example
	 *
	 * var object = { 'a': 1 };
	 * var other = { 'a': 1 };
	 *
	 * _.eq(object, object);
	 * // => true
	 *
	 * _.eq(object, other);
	 * // => false
	 *
	 * _.eq('a', 'a');
	 * // => true
	 *
	 * _.eq('a', Object('a'));
	 * // => false
	 *
	 * _.eq(NaN, NaN);
	 * // => true
	 */
	function eq(value, other) {
	  return value === other || (value !== value && other !== other);
	}

	/**
	 * Checks if `value` is likely an `arguments` object.
	 *
	 * @static
	 * @memberOf _
	 * @since 0.1.0
	 * @category Lang
	 * @param {*} value The value to check.
	 * @returns {boolean} Returns `true` if `value` is an `arguments` object,
	 *  else `false`.
	 * @example
	 *
	 * _.isArguments(function() { return arguments; }());
	 * // => true
	 *
	 * _.isArguments([1, 2, 3]);
	 * // => false
	 */
	function isArguments(value) {
	  // Safari 8.1 makes `arguments.callee` enumerable in strict mode.
	  return isArrayLikeObject(value) && hasOwnProperty.call(value, 'callee') &&
	    (!propertyIsEnumerable.call(value, 'callee') || objectToString.call(value) == argsTag);
	}

	/**
	 * Checks if `value` is classified as an `Array` object.
	 *
	 * @static
	 * @memberOf _
	 * @since 0.1.0
	 * @category Lang
	 * @param {*} value The value to check.
	 * @returns {boolean} Returns `true` if `value` is an array, else `false`.
	 * @example
	 *
	 * _.isArray([1, 2, 3]);
	 * // => true
	 *
	 * _.isArray(document.body.children);
	 * // => false
	 *
	 * _.isArray('abc');
	 * // => false
	 *
	 * _.isArray(_.noop);
	 * // => false
	 */
	var isArray = Array.isArray;

	/**
	 * Checks if `value` is array-like. A value is considered array-like if it's
	 * not a function and has a `value.length` that's an integer greater than or
	 * equal to `0` and less than or equal to `Number.MAX_SAFE_INTEGER`.
	 *
	 * @static
	 * @memberOf _
	 * @since 4.0.0
	 * @category Lang
	 * @param {*} value The value to check.
	 * @returns {boolean} Returns `true` if `value` is array-like, else `false`.
	 * @example
	 *
	 * _.isArrayLike([1, 2, 3]);
	 * // => true
	 *
	 * _.isArrayLike(document.body.children);
	 * // => true
	 *
	 * _.isArrayLike('abc');
	 * // => true
	 *
	 * _.isArrayLike(_.noop);
	 * // => false
	 */
	function isArrayLike(value) {
	  return value != null && isLength(value.length) && !isFunction(value);
	}

	/**
	 * This method is like `_.isArrayLike` except that it also checks if `value`
	 * is an object.
	 *
	 * @static
	 * @memberOf _
	 * @since 4.0.0
	 * @category Lang
	 * @param {*} value The value to check.
	 * @returns {boolean} Returns `true` if `value` is an array-like object,
	 *  else `false`.
	 * @example
	 *
	 * _.isArrayLikeObject([1, 2, 3]);
	 * // => true
	 *
	 * _.isArrayLikeObject(document.body.children);
	 * // => true
	 *
	 * _.isArrayLikeObject('abc');
	 * // => false
	 *
	 * _.isArrayLikeObject(_.noop);
	 * // => false
	 */
	function isArrayLikeObject(value) {
	  return isObjectLike(value) && isArrayLike(value);
	}

	/**
	 * Checks if `value` is an `Error`, `EvalError`, `RangeError`, `ReferenceError`,
	 * `SyntaxError`, `TypeError`, or `URIError` object.
	 *
	 * @static
	 * @memberOf _
	 * @since 3.0.0
	 * @category Lang
	 * @param {*} value The value to check.
	 * @returns {boolean} Returns `true` if `value` is an error object, else `false`.
	 * @example
	 *
	 * _.isError(new Error);
	 * // => true
	 *
	 * _.isError(Error);
	 * // => false
	 */
	function isError(value) {
	  if (!isObjectLike(value)) {
	    return false;
	  }
	  return (objectToString.call(value) == errorTag) ||
	    (typeof value.message == 'string' && typeof value.name == 'string');
	}

	/**
	 * Checks if `value` is classified as a `Function` object.
	 *
	 * @static
	 * @memberOf _
	 * @since 0.1.0
	 * @category Lang
	 * @param {*} value The value to check.
	 * @returns {boolean} Returns `true` if `value` is a function, else `false`.
	 * @example
	 *
	 * _.isFunction(_);
	 * // => true
	 *
	 * _.isFunction(/abc/);
	 * // => false
	 */
	function isFunction(value) {
	  // The use of `Object#toString` avoids issues with the `typeof` operator
	  // in Safari 8-9 which returns 'object' for typed array and other constructors.
	  var tag = isObject(value) ? objectToString.call(value) : '';
	  return tag == funcTag || tag == genTag;
	}

	/**
	 * Checks if `value` is a valid array-like length.
	 *
	 * **Note:** This method is loosely based on
	 * [`ToLength`](http://ecma-international.org/ecma-262/7.0/#sec-tolength).
	 *
	 * @static
	 * @memberOf _
	 * @since 4.0.0
	 * @category Lang
	 * @param {*} value The value to check.
	 * @returns {boolean} Returns `true` if `value` is a valid length, else `false`.
	 * @example
	 *
	 * _.isLength(3);
	 * // => true
	 *
	 * _.isLength(Number.MIN_VALUE);
	 * // => false
	 *
	 * _.isLength(Infinity);
	 * // => false
	 *
	 * _.isLength('3');
	 * // => false
	 */
	function isLength(value) {
	  return typeof value == 'number' &&
	    value > -1 && value % 1 == 0 && value <= MAX_SAFE_INTEGER;
	}

	/**
	 * Checks if `value` is the
	 * [language type](http://www.ecma-international.org/ecma-262/7.0/#sec-ecmascript-language-types)
	 * of `Object`. (e.g. arrays, functions, objects, regexes, `new Number(0)`, and `new String('')`)
	 *
	 * @static
	 * @memberOf _
	 * @since 0.1.0
	 * @category Lang
	 * @param {*} value The value to check.
	 * @returns {boolean} Returns `true` if `value` is an object, else `false`.
	 * @example
	 *
	 * _.isObject({});
	 * // => true
	 *
	 * _.isObject([1, 2, 3]);
	 * // => true
	 *
	 * _.isObject(_.noop);
	 * // => true
	 *
	 * _.isObject(null);
	 * // => false
	 */
	function isObject(value) {
	  var type = typeof value;
	  return !!value && (type == 'object' || type == 'function');
	}

	/**
	 * Checks if `value` is object-like. A value is object-like if it's not `null`
	 * and has a `typeof` result of "object".
	 *
	 * @static
	 * @memberOf _
	 * @since 4.0.0
	 * @category Lang
	 * @param {*} value The value to check.
	 * @returns {boolean} Returns `true` if `value` is object-like, else `false`.
	 * @example
	 *
	 * _.isObjectLike({});
	 * // => true
	 *
	 * _.isObjectLike([1, 2, 3]);
	 * // => true
	 *
	 * _.isObjectLike(_.noop);
	 * // => false
	 *
	 * _.isObjectLike(null);
	 * // => false
	 */
	function isObjectLike(value) {
	  return !!value && typeof value == 'object';
	}

	/**
	 * Checks if `value` is classified as a `Symbol` primitive or object.
	 *
	 * @static
	 * @memberOf _
	 * @since 4.0.0
	 * @category Lang
	 * @param {*} value The value to check.
	 * @returns {boolean} Returns `true` if `value` is a symbol, else `false`.
	 * @example
	 *
	 * _.isSymbol(Symbol.iterator);
	 * // => true
	 *
	 * _.isSymbol('abc');
	 * // => false
	 */
	function isSymbol(value) {
	  return typeof value == 'symbol' ||
	    (isObjectLike(value) && objectToString.call(value) == symbolTag);
	}

	/**
	 * Converts `value` to a string. An empty string is returned for `null`
	 * and `undefined` values. The sign of `-0` is preserved.
	 *
	 * @static
	 * @memberOf _
	 * @since 4.0.0
	 * @category Lang
	 * @param {*} value The value to process.
	 * @returns {string} Returns the string.
	 * @example
	 *
	 * _.toString(null);
	 * // => ''
	 *
	 * _.toString(-0);
	 * // => '-0'
	 *
	 * _.toString([1, 2, 3]);
	 * // => '1,2,3'
	 */
	function toString(value) {
	  return value == null ? '' : baseToString(value);
	}

	/**
	 * This method is like `_.assignIn` except that it accepts `customizer`
	 * which is invoked to produce the assigned values. If `customizer` returns
	 * `undefined`, assignment is handled by the method instead. The `customizer`
	 * is invoked with five arguments: (objValue, srcValue, key, object, source).
	 *
	 * **Note:** This method mutates `object`.
	 *
	 * @static
	 * @memberOf _
	 * @since 4.0.0
	 * @alias extendWith
	 * @category Object
	 * @param {Object} object The destination object.
	 * @param {...Object} sources The source objects.
	 * @param {Function} [customizer] The function to customize assigned values.
	 * @returns {Object} Returns `object`.
	 * @see _.assignWith
	 * @example
	 *
	 * function customizer(objValue, srcValue) {
	 *   return _.isUndefined(objValue) ? srcValue : objValue;
	 * }
	 *
	 * var defaults = _.partialRight(_.assignInWith, customizer);
	 *
	 * defaults({ 'a': 1 }, { 'b': 2 }, { 'a': 3 });
	 * // => { 'a': 1, 'b': 2 }
	 */
	var assignInWith = createAssigner(function(object, source, srcIndex, customizer) {
	  copyObject(source, keysIn(source), object, customizer);
	});

	/**
	 * Creates an array of the own enumerable property names of `object`.
	 *
	 * **Note:** Non-object values are coerced to objects. See the
	 * [ES spec](http://ecma-international.org/ecma-262/7.0/#sec-object.keys)
	 * for more details.
	 *
	 * @static
	 * @since 0.1.0
	 * @memberOf _
	 * @category Object
	 * @param {Object} object The object to query.
	 * @returns {Array} Returns the array of property names.
	 * @example
	 *
	 * function Foo() {
	 *   this.a = 1;
	 *   this.b = 2;
	 * }
	 *
	 * Foo.prototype.c = 3;
	 *
	 * _.keys(new Foo);
	 * // => ['a', 'b'] (iteration order is not guaranteed)
	 *
	 * _.keys('hi');
	 * // => ['0', '1']
	 */
	function keys(object) {
	  return isArrayLike(object) ? arrayLikeKeys(object) : baseKeys(object);
	}

	/**
	 * Creates an array of the own and inherited enumerable property names of `object`.
	 *
	 * **Note:** Non-object values are coerced to objects.
	 *
	 * @static
	 * @memberOf _
	 * @since 3.0.0
	 * @category Object
	 * @param {Object} object The object to query.
	 * @returns {Array} Returns the array of property names.
	 * @example
	 *
	 * function Foo() {
	 *   this.a = 1;
	 *   this.b = 2;
	 * }
	 *
	 * Foo.prototype.c = 3;
	 *
	 * _.keysIn(new Foo);
	 * // => ['a', 'b', 'c'] (iteration order is not guaranteed)
	 */
	function keysIn(object) {
	  return isArrayLike(object) ? arrayLikeKeys(object, true) : baseKeysIn(object);
	}

	/**
	 * Creates a compiled template function that can interpolate data properties
	 * in "interpolate" delimiters, HTML-escape interpolated data properties in
	 * "escape" delimiters, and execute JavaScript in "evaluate" delimiters. Data
	 * properties may be accessed as free variables in the template. If a setting
	 * object is given, it takes precedence over `_.templateSettings` values.
	 *
	 * **Note:** In the development build `_.template` utilizes
	 * [sourceURLs](http://www.html5rocks.com/en/tutorials/developertools/sourcemaps/#toc-sourceurl)
	 * for easier debugging.
	 *
	 * For more information on precompiling templates see
	 * [lodash's custom builds documentation](https://lodash.com/custom-builds).
	 *
	 * For more information on Chrome extension sandboxes see
	 * [Chrome's extensions documentation](https://developer.chrome.com/extensions/sandboxingEval).
	 *
	 * @static
	 * @since 0.1.0
	 * @memberOf _
	 * @category String
	 * @param {string} [string=''] The template string.
	 * @param {Object} [options={}] The options object.
	 * @param {RegExp} [options.escape=_.templateSettings.escape]
	 *  The HTML "escape" delimiter.
	 * @param {RegExp} [options.evaluate=_.templateSettings.evaluate]
	 *  The "evaluate" delimiter.
	 * @param {Object} [options.imports=_.templateSettings.imports]
	 *  An object to import into the template as free variables.
	 * @param {RegExp} [options.interpolate=_.templateSettings.interpolate]
	 *  The "interpolate" delimiter.
	 * @param {string} [options.sourceURL='templateSources[n]']
	 *  The sourceURL of the compiled template.
	 * @param {string} [options.variable='obj']
	 *  The data object variable name.
	 * @param- {Object} [guard] Enables use as an iteratee for methods like `_.map`.
	 * @returns {Function} Returns the compiled template function.
	 * @example
	 *
	 * // Use the "interpolate" delimiter to create a compiled template.
	 * var compiled = _.template('hello <%= user %>!');
	 * compiled({ 'user': 'fred' });
	 * // => 'hello fred!'
	 *
	 * // Use the HTML "escape" delimiter to escape data property values.
	 * var compiled = _.template('<b><%- value %></b>');
	 * compiled({ 'value': '<script>' });
	 * // => '<b>&lt;script&gt;</b>'
	 *
	 * // Use the "evaluate" delimiter to execute JavaScript and generate HTML.
	 * var compiled = _.template('<% _.forEach(users, function(user) { %><li><%- user %></li><% }); %>');
	 * compiled({ 'users': ['fred', 'barney'] });
	 * // => '<li>fred</li><li>barney</li>'
	 *
	 * // Use the internal `print` function in "evaluate" delimiters.
	 * var compiled = _.template('<% print("hello " + user); %>!');
	 * compiled({ 'user': 'barney' });
	 * // => 'hello barney!'
	 *
	 * // Use the ES delimiter as an alternative to the default "interpolate" delimiter.
	 * var compiled = _.template('hello ${ user }!');
	 * compiled({ 'user': 'pebbles' });
	 * // => 'hello pebbles!'
	 *
	 * // Use backslashes to treat delimiters as plain text.
	 * var compiled = _.template('<%= "\\<%- value %\\>" %>');
	 * compiled({ 'value': 'ignored' });
	 * // => '<%- value %>'
	 *
	 * // Use the `imports` option to import `jQuery` as `jq`.
	 * var text = '<% jq.each(users, function(user) { %><li><%- user %></li><% }); %>';
	 * var compiled = _.template(text, { 'imports': { 'jq': jQuery } });
	 * compiled({ 'users': ['fred', 'barney'] });
	 * // => '<li>fred</li><li>barney</li>'
	 *
	 * // Use the `sourceURL` option to specify a custom sourceURL for the template.
	 * var compiled = _.template('hello <%= user %>!', { 'sourceURL': '/basic/greeting.jst' });
	 * compiled(data);
	 * // => Find the source of "greeting.jst" under the Sources tab or Resources panel of the web inspector.
	 *
	 * // Use the `variable` option to ensure a with-statement isn't used in the compiled template.
	 * var compiled = _.template('hi <%= data.user %>!', { 'variable': 'data' });
	 * compiled.source;
	 * // => function(data) {
	 * //   var __t, __p = '';
	 * //   __p += 'hi ' + ((__t = ( data.user )) == null ? '' : __t) + '!';
	 * //   return __p;
	 * // }
	 *
	 * // Use custom template delimiters.
	 * _.templateSettings.interpolate = /{{([\s\S]+?)}}/g;
	 * var compiled = _.template('hello {{ user }}!');
	 * compiled({ 'user': 'mustache' });
	 * // => 'hello mustache!'
	 *
	 * // Use the `source` property to inline compiled templates for meaningful
	 * // line numbers in error messages and stack traces.
	 * fs.writeFileSync(path.join(process.cwd(), 'jst.js'), '\
	 *   var JST = {\
	 *     "main": ' + _.template(mainText).source + '\
	 *   };\
	 * ');
	 */
	function template(string, options, guard) {
	  // Based on John Resig's `tmpl` implementation
	  // (http://ejohn.org/blog/javascript-micro-templating/)
	  // and Laura Doktorova's doT.js (https://github.com/olado/doT).
	  var settings = templateSettings.imports._.templateSettings || templateSettings;

	  if (guard && isIterateeCall(string, options, guard)) {
	    options = undefined;
	  }
	  string = toString(string);
	  options = assignInWith({}, options, settings, assignInDefaults);

	  var imports = assignInWith({}, options.imports, settings.imports, assignInDefaults),
	      importsKeys = keys(imports),
	      importsValues = baseValues(imports, importsKeys);

	  var isEscaping,
	      isEvaluating,
	      index = 0,
	      interpolate = options.interpolate || reNoMatch,
	      source = "__p += '";

	  // Compile the regexp to match each delimiter.
	  var reDelimiters = RegExp(
	    (options.escape || reNoMatch).source + '|' +
	    interpolate.source + '|' +
	    (interpolate === reInterpolate ? reEsTemplate : reNoMatch).source + '|' +
	    (options.evaluate || reNoMatch).source + '|$'
	  , 'g');

	  // Use a sourceURL for easier debugging.
	  var sourceURL = 'sourceURL' in options ? '//# sourceURL=' + options.sourceURL + '\n' : '';

	  string.replace(reDelimiters, function(match, escapeValue, interpolateValue, esTemplateValue, evaluateValue, offset) {
	    interpolateValue || (interpolateValue = esTemplateValue);

	    // Escape characters that can't be included in string literals.
	    source += string.slice(index, offset).replace(reUnescapedString, escapeStringChar);

	    // Replace delimiters with snippets.
	    if (escapeValue) {
	      isEscaping = true;
	      source += "' +\n__e(" + escapeValue + ") +\n'";
	    }
	    if (evaluateValue) {
	      isEvaluating = true;
	      source += "';\n" + evaluateValue + ";\n__p += '";
	    }
	    if (interpolateValue) {
	      source += "' +\n((__t = (" + interpolateValue + ")) == null ? '' : __t) +\n'";
	    }
	    index = offset + match.length;

	    // The JS engine embedded in Adobe products needs `match` returned in
	    // order to produce the correct `offset` value.
	    return match;
	  });

	  source += "';\n";

	  // If `variable` is not specified wrap a with-statement around the generated
	  // code to add the data object to the top of the scope chain.
	  var variable = options.variable;
	  if (!variable) {
	    source = 'with (obj) {\n' + source + '\n}\n';
	  }
	  // Cleanup code by stripping empty strings.
	  source = (isEvaluating ? source.replace(reEmptyStringLeading, '') : source)
	    .replace(reEmptyStringMiddle, '$1')
	    .replace(reEmptyStringTrailing, '$1;');

	  // Frame code as the function body.
	  source = 'function(' + (variable || 'obj') + ') {\n' +
	    (variable
	      ? ''
	      : 'obj || (obj = {});\n'
	    ) +
	    "var __t, __p = ''" +
	    (isEscaping
	       ? ', __e = _.escape'
	       : ''
	    ) +
	    (isEvaluating
	      ? ', __j = Array.prototype.join;\n' +
	        "function print() { __p += __j.call(arguments, '') }\n"
	      : ';\n'
	    ) +
	    source +
	    'return __p\n}';

	  var result = attempt(function() {
	    return Function(importsKeys, sourceURL + 'return ' + source)
	      .apply(undefined, importsValues);
	  });

	  // Provide the compiled function's source by its `toString` method or
	  // the `source` property as a convenience for inlining compiled templates.
	  result.source = source;
	  if (isError(result)) {
	    throw result;
	  }
	  return result;
	}

	/**
	 * Attempts to invoke `func`, returning either the result or the caught error
	 * object. Any additional arguments are provided to `func` when it's invoked.
	 *
	 * @static
	 * @memberOf _
	 * @since 3.0.0
	 * @category Util
	 * @param {Function} func The function to attempt.
	 * @param {...*} [args] The arguments to invoke `func` with.
	 * @returns {*} Returns the `func` result or error object.
	 * @example
	 *
	 * // Avoid throwing errors for invalid selectors.
	 * var elements = _.attempt(function(selector) {
	 *   return document.querySelectorAll(selector);
	 * }, '>_>');
	 *
	 * if (_.isError(elements)) {
	 *   elements = [];
	 * }
	 */
	var attempt = baseRest(function(func, args) {
	  try {
	    return apply(func, undefined, args);
	  } catch (e) {
	    return isError(e) ? e : new Error(e);
	  }
	});

	module.exports = template;

	/* WEBPACK VAR INJECTION */}.call(exports, (function() { return this; }())))

/***/ },
/* 14 */
/***/ function(module, exports) {

	/**
	 * lodash 3.0.0 (Custom Build) <https://lodash.com/>
	 * Build: `lodash modern modularize exports="npm" -o ./`
	 * Copyright 2012-2015 The Dojo Foundation <http://dojofoundation.org/>
	 * Based on Underscore.js 1.7.0 <http://underscorejs.org/LICENSE>
	 * Copyright 2009-2015 Jeremy Ashkenas, DocumentCloud and Investigative Reporters & Editors
	 * Available under MIT license <https://lodash.com/license>
	 */

	/** Used to match template delimiters. */
	var reInterpolate = /<%=([\s\S]+?)%>/g;

	module.exports = reInterpolate;


/***/ },
/* 15 */
/***/ function(module, exports, __webpack_require__) {

	/* WEBPACK VAR INJECTION */(function(global) {/**
	 * lodash (Custom Build) <https://lodash.com/>
	 * Build: `lodash modularize exports="npm" -o ./`
	 * Copyright jQuery Foundation and other contributors <https://jquery.org/>
	 * Released under MIT license <https://lodash.com/license>
	 * Based on Underscore.js 1.8.3 <http://underscorejs.org/LICENSE>
	 * Copyright Jeremy Ashkenas, DocumentCloud and Investigative Reporters & Editors
	 */
	var reInterpolate = __webpack_require__(14);

	/** Used as references for various `Number` constants. */
	var INFINITY = 1 / 0;

	/** `Object#toString` result references. */
	var symbolTag = '[object Symbol]';

	/** Used to match HTML entities and HTML characters. */
	var reUnescapedHtml = /[&<>"'`]/g,
	    reHasUnescapedHtml = RegExp(reUnescapedHtml.source);

	/** Used to match template delimiters. */
	var reEscape = /<%-([\s\S]+?)%>/g,
	    reEvaluate = /<%([\s\S]+?)%>/g;

	/** Used to map characters to HTML entities. */
	var htmlEscapes = {
	  '&': '&amp;',
	  '<': '&lt;',
	  '>': '&gt;',
	  '"': '&quot;',
	  "'": '&#39;',
	  '`': '&#96;'
	};

	/** Detect free variable `global` from Node.js. */
	var freeGlobal = typeof global == 'object' && global && global.Object === Object && global;

	/** Detect free variable `self`. */
	var freeSelf = typeof self == 'object' && self && self.Object === Object && self;

	/** Used as a reference to the global object. */
	var root = freeGlobal || freeSelf || Function('return this')();

	/**
	 * The base implementation of `_.propertyOf` without support for deep paths.
	 *
	 * @private
	 * @param {Object} object The object to query.
	 * @returns {Function} Returns the new accessor function.
	 */
	function basePropertyOf(object) {
	  return function(key) {
	    return object == null ? undefined : object[key];
	  };
	}

	/**
	 * Used by `_.escape` to convert characters to HTML entities.
	 *
	 * @private
	 * @param {string} chr The matched character to escape.
	 * @returns {string} Returns the escaped character.
	 */
	var escapeHtmlChar = basePropertyOf(htmlEscapes);

	/** Used for built-in method references. */
	var objectProto = Object.prototype;

	/**
	 * Used to resolve the
	 * [`toStringTag`](http://ecma-international.org/ecma-262/6.0/#sec-object.prototype.tostring)
	 * of values.
	 */
	var objectToString = objectProto.toString;

	/** Built-in value references. */
	var Symbol = root.Symbol;

	/** Used to convert symbols to primitives and strings. */
	var symbolProto = Symbol ? Symbol.prototype : undefined,
	    symbolToString = symbolProto ? symbolProto.toString : undefined;

	/**
	 * By default, the template delimiters used by lodash are like those in
	 * embedded Ruby (ERB). Change the following template settings to use
	 * alternative delimiters.
	 *
	 * @static
	 * @memberOf _
	 * @type {Object}
	 */
	var templateSettings = {

	  /**
	   * Used to detect `data` property values to be HTML-escaped.
	   *
	   * @memberOf _.templateSettings
	   * @type {RegExp}
	   */
	  'escape': reEscape,

	  /**
	   * Used to detect code to be evaluated.
	   *
	   * @memberOf _.templateSettings
	   * @type {RegExp}
	   */
	  'evaluate': reEvaluate,

	  /**
	   * Used to detect `data` property values to inject.
	   *
	   * @memberOf _.templateSettings
	   * @type {RegExp}
	   */
	  'interpolate': reInterpolate,

	  /**
	   * Used to reference the data object in the template text.
	   *
	   * @memberOf _.templateSettings
	   * @type {string}
	   */
	  'variable': '',

	  /**
	   * Used to import variables into the compiled template.
	   *
	   * @memberOf _.templateSettings
	   * @type {Object}
	   */
	  'imports': {

	    /**
	     * A reference to the `lodash` function.
	     *
	     * @memberOf _.templateSettings.imports
	     * @type {Function}
	     */
	    '_': { 'escape': escape }
	  }
	};

	/**
	 * The base implementation of `_.toString` which doesn't convert nullish
	 * values to empty strings.
	 *
	 * @private
	 * @param {*} value The value to process.
	 * @returns {string} Returns the string.
	 */
	function baseToString(value) {
	  // Exit early for strings to avoid a performance hit in some environments.
	  if (typeof value == 'string') {
	    return value;
	  }
	  if (isSymbol(value)) {
	    return symbolToString ? symbolToString.call(value) : '';
	  }
	  var result = (value + '');
	  return (result == '0' && (1 / value) == -INFINITY) ? '-0' : result;
	}

	/**
	 * Checks if `value` is object-like. A value is object-like if it's not `null`
	 * and has a `typeof` result of "object".
	 *
	 * @static
	 * @memberOf _
	 * @since 4.0.0
	 * @category Lang
	 * @param {*} value The value to check.
	 * @returns {boolean} Returns `true` if `value` is object-like, else `false`.
	 * @example
	 *
	 * _.isObjectLike({});
	 * // => true
	 *
	 * _.isObjectLike([1, 2, 3]);
	 * // => true
	 *
	 * _.isObjectLike(_.noop);
	 * // => false
	 *
	 * _.isObjectLike(null);
	 * // => false
	 */
	function isObjectLike(value) {
	  return !!value && typeof value == 'object';
	}

	/**
	 * Checks if `value` is classified as a `Symbol` primitive or object.
	 *
	 * @static
	 * @memberOf _
	 * @since 4.0.0
	 * @category Lang
	 * @param {*} value The value to check.
	 * @returns {boolean} Returns `true` if `value` is a symbol, else `false`.
	 * @example
	 *
	 * _.isSymbol(Symbol.iterator);
	 * // => true
	 *
	 * _.isSymbol('abc');
	 * // => false
	 */
	function isSymbol(value) {
	  return typeof value == 'symbol' ||
	    (isObjectLike(value) && objectToString.call(value) == symbolTag);
	}

	/**
	 * Converts `value` to a string. An empty string is returned for `null`
	 * and `undefined` values. The sign of `-0` is preserved.
	 *
	 * @static
	 * @memberOf _
	 * @since 4.0.0
	 * @category Lang
	 * @param {*} value The value to process.
	 * @returns {string} Returns the string.
	 * @example
	 *
	 * _.toString(null);
	 * // => ''
	 *
	 * _.toString(-0);
	 * // => '-0'
	 *
	 * _.toString([1, 2, 3]);
	 * // => '1,2,3'
	 */
	function toString(value) {
	  return value == null ? '' : baseToString(value);
	}

	/**
	 * Converts the characters "&", "<", ">", '"', "'", and "\`" in `string` to
	 * their corresponding HTML entities.
	 *
	 * **Note:** No other characters are escaped. To escape additional
	 * characters use a third-party library like [_he_](https://mths.be/he).
	 *
	 * Though the ">" character is escaped for symmetry, characters like
	 * ">" and "/" don't need escaping in HTML and have no special meaning
	 * unless they're part of a tag or unquoted attribute value. See
	 * [Mathias Bynens's article](https://mathiasbynens.be/notes/ambiguous-ampersands)
	 * (under "semi-related fun fact") for more details.
	 *
	 * Backticks are escaped because in IE < 9, they can break out of
	 * attribute values or HTML comments. See [#59](https://html5sec.org/#59),
	 * [#102](https://html5sec.org/#102), [#108](https://html5sec.org/#108), and
	 * [#133](https://html5sec.org/#133) of the
	 * [HTML5 Security Cheatsheet](https://html5sec.org/) for more details.
	 *
	 * When working with HTML you should always
	 * [quote attribute values](http://wonko.com/post/html-escaping) to reduce
	 * XSS vectors.
	 *
	 * @static
	 * @since 0.1.0
	 * @memberOf _
	 * @category String
	 * @param {string} [string=''] The string to escape.
	 * @returns {string} Returns the escaped string.
	 * @example
	 *
	 * _.escape('fred, barney, & pebbles');
	 * // => 'fred, barney, &amp; pebbles'
	 */
	function escape(string) {
	  string = toString(string);
	  return (string && reHasUnescapedHtml.test(string))
	    ? string.replace(reUnescapedHtml, escapeHtmlChar)
	    : string;
	}

	module.exports = templateSettings;

	/* WEBPACK VAR INJECTION */}.call(exports, (function() { return this; }())))

/***/ }
/******/ ]);