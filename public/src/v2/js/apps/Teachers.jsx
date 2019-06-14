import React, {Fragment} from 'react';
import { forceCheck } from 'react-lazyload';

import _debounce from 'lodash-es/debounce';
import _includes from 'lodash-es/includes';
import $ from 'jquery';

import Select from 'components/Select';
import SelectLazy from "components/SelectLazy";
import SearchInput from 'components/SearchInput';
import UserCardList from 'components/UserCardList';
import {
    hideBodyPreloader,
    showBodyPreloader,
    showErrorNotification
} from "utils";


class App extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            "loading": true,
            "items": [],
            "query": "",
            "course": null,
            "recentOnly": true,
            ...props.initialState
        };
        this.fetch = _debounce(this.fetch, 300);
        this.CourseSelect = React.createRef();
    }

    handleSearchInputChange = (value) => {
        this.setState({
            query: value,
        });
    };

    handleCityChange = (city) => {
        this.setState({
            city: city
        });
    };

    handleCourseChange = (course) => {
        this.setState({
            course: course
        });
    };

    handleRecentCheckboxChange = () => {
        this.setState({
            recentOnly: !this.state.recentOnly
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
        let {query, city, course} = state;
        let filterState = {query, city, course};
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
            url: this.props.entry_url,
            dataType: "json",
            data: payload
        }).done((data) => {
            data.forEach((item) => {
               item.courses = new Set(item.courses);
               item.url = `/teachers/${item.id}`;
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

    handleLoadCourseOptions(select, callback) {
        console.debug("Teachers: load course list options");
        $.ajax({
            type: "GET",
            url: select.props.entry_url,
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
            })
        }).fail(() => {
            showErrorNotification("Ошибка загрузки данных. Попробуйте перезагрузить страницу.");
        });
    };

    render() {
        if (this.state.loading) {
            showBodyPreloader();
        }
        //TODO: prevent rerendering if query < 3 symbols
        const {query, city, course, recentOnly} = this.state;
        const {term_index, cities} = this.props;
        let filteredItems = this.state.items.filter(function(item) {
            let cityCondition = (city !== null) ? item.city === city.value : true;
            let courseCondition = (course !== null) ? item.courses.has(course.value) : true;
            let activityCondition = recentOnly ? item.last_session >= term_index: true;
            return cityCondition && courseCondition && activityCondition &&
                   _includes(item.name.toLowerCase(), query.toLowerCase());
        });

        return (
            <Fragment>
                <h1>Преподаватели</h1>
                <div className="row mb-4">
                    <div className="col-lg-3 mb-4">
                        <SearchInput
                            onChange={this.handleSearchInputChange}
                            placeholder="Поиск"
                            value={query}
                            icon="search"
                        />
                    </div>
                    <div className="col-lg-3 mb-4">
                        <Select
                            onChange={this.handleCityChange}
                            value={city}
                            name="city"
                            isClearable={true}
                            placeholder="Город"
                            options={cities}
                            key="city"
                        />
                    </div>
                    <div className="col-lg-3 mb-4">
                        <SelectLazy
                            onChange={this.handleCourseChange}
                            value={course}
                            name="course"
                            isClearable={true}
                            placeholder="Предмет"
                            key="course"
                            handleLoadOptions={this.handleLoadCourseOptions}
                            entry_url={this.props.courses_url}
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

export default App;