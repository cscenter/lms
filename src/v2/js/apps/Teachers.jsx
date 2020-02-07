import React, {Fragment} from 'react';
import * as PropTypes from 'prop-types';

import _throttle from 'lodash-es/throttle';
import _includes from 'lodash-es/includes';
import _cloneDeep from 'lodash-es/cloneDeep';
import $ from 'jquery';

import {Select} from 'components/Select';
import SelectLazyOptions from "components/SelectLazyOptions";
import SearchInput from 'components/SearchInput';
import UserCardList from 'components/UserCardList';
import {
    hideBodyPreloader,
    loadIntersectionObserverPolyfill,
    showBodyPreloader,
    showErrorNotification
} from "utils";
import {onSearchInputChange, onSelectChange} from "components/utils";

export let polyfills = [
    loadIntersectionObserverPolyfill(),
];


class App extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            "loading": true,
            "items": [],
            "query": "",
            "course": null,
            "recentOnly": true,
            ..._cloneDeep(props.initialState)
        };
        this.fetch = _throttle(this.fetch, 300);
        this.CourseSelect = React.createRef();
    }

    handleSearchInputChange = onSearchInputChange.bind(this);

    handleSelectChange = onSelectChange.bind(this);

    handleRecentCheckboxChange = () => {
        this.setState(state => {
            return {
                recentOnly: !state.recentOnly
            }
        });
    };

    componentDidMount = () => {
        const filterState = this.getFilterState(this.state);
        console.debug("Teachers: filterState", filterState);
        const newPayload = this.getRequestPayload(filterState);
        console.debug("Teachers: newPayload", newPayload);
        this.fetch(newPayload);
    };

    componentWillUnmount = function () {
        this.serverRequest.abort();
    };

    componentDidUpdate(prevProps, prevState) {
        if (this.state.loading) {
            const filterState = this.getFilterState(this.state);
            const newPayload = this.getRequestPayload(filterState);
            this.fetch(newPayload);
        } else {
            hideBodyPreloader();
        }
    };

    getFilterState(state) {
        let {query, branch, course} = state;
        let filterState = {query, branch, course};
        Object.keys(filterState).map((k) => {
            if (k === "course" && filterState[k] !== null) {
                filterState[k] = filterState[k]["value"];
            }
            // Convert null and undefined to empty string
            filterState[k] = !filterState[k] ? "" : filterState[k];
        });
        return filterState;
    }

    getRequestPayload(filterState) {
        let {course} = filterState;
        return {course};
    }

    fetch = (payload) => {
        console.debug("Teachers: fetch", this.props, payload);
        this.serverRequest = $.ajax({
            type: "GET",
            url: this.props.endpoint,
            dataType: "json",
            data: payload
        }).done((data) => {
            data.forEach((item) => {
               item.courses = new Set(item.courses);
               item.url = `/teachers/${item.id}/`;
            });
            this.setState({
                loading: false,
                items: data,
            });
            this.CourseSelect.current.setState({isLoading: false});
        }).fail(() => {
            showErrorNotification("Ошибка загрузки данных. Попробуйте перезагрузить страницу.");
        });
    };

    handleLoadCourseOptions(select) {
        console.debug("Teachers: load course list options");
        $.ajax({
            type: "GET",
            url: select.props.endpoint,
            dataType: "json"
        }).done((data) => {
            let options = [];
            data.forEach((item) => {
               options.push({value: item.id, label: item.name});
            });
            select.setState({
                optionsLoaded: true,
                options,
                isLoading: false
            });
        }).fail(() => {
            showErrorNotification("Ошибка загрузки данных. Попробуйте перезагрузить страницу.");
        });
    }

    render() {
        if (this.state.loading) {
            showBodyPreloader();
        }
        //TODO: prevent rerendering if query < 3 symbols
        const {query, branch, course, recentOnly} = this.state;
        const {termIndex, branchOptions} = this.props;
        let filteredItems = this.state.items.filter(function(item) {
            let branchCondition = (branch !== null) ? item.branch === branch.value : true;
            let courseCondition = (course !== null) ? item.courses.has(course.value) : true;
            let activityCondition = recentOnly ? item.latest_session >= termIndex: true;
            return branchCondition && courseCondition && activityCondition &&
                   _includes(item.name.toLowerCase(), query.toLowerCase());
        });

        return (
            <Fragment>
                <h1>Преподаватели</h1>
                <div className="row mb-4">
                    <div className="col-lg-3 mb-4">
                        <SearchInput
                            handleSearch={this.handleSearchInputChange}
                            query={query}
                            name="query"
                            placeholder="Поиск"
                            icon="search"
                        />
                    </div>
                    <div className="col-lg-3 mb-4">
                        <Select
                            onChange={this.handleSelectChange}
                            value={branch}
                            name="branch"
                            isClearable={true}
                            placeholder="Город"
                            options={branchOptions}
                            key="branch"
                        />
                    </div>
                    <div className="col-lg-3 mb-4">
                        <SelectLazyOptions
                            onChange={this.handleSelectChange}
                            value={course}
                            name="course"
                            isClearable={true}
                            placeholder="Предмет"
                            key="course"
                            handleLoadOptions={this.handleLoadCourseOptions}
                            endpoint={this.props.coursesURL}
                            ref={this.CourseSelect}
                        />
                    </div>
                    <div className="col-lg-3 mb-4">
                        <div className="grouped inline">
                            <label className="ui option checkbox">
                                <input type="checkbox"
                                       className="control__input"
                                       checked={!this.state.recentOnly}
                                       onChange={this.handleRecentCheckboxChange}
                                       value=""
                                />
                                <span className="control__indicator" />
                                <span className="control__description">Ранее преподавали</span>
                            </label>
                        </div>
                    </div>
                </div>
                {
                    filteredItems.length > 0 ?
                        <UserCardList users={filteredItems} />
                        : "Выберите другие параметры фильтрации."
                }
            </Fragment>
        );
    }
}

const propTypes = {
    endpoint: PropTypes.string.isRequired,
    coursesURL: PropTypes.string.isRequired,
    termIndex: PropTypes.number.isRequired,
    branchOptions: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired
    })).isRequired,
};

App.propTypes = propTypes;

export default App;