import React, {Fragment} from 'react';

import _throttle from 'lodash-es/throttle';
import $ from 'jquery';
import PropTypes from 'prop-types';

import SelectLazy from "components/SelectLazy";
import SearchInput from 'components/SearchInput';
import {
    hideBodyPreloader,
    showBodyPreloader,
    showErrorNotification
} from "utils";
import Select from "../components/Select";


class CourseVideosPage extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            "loading": true,
            "items": [],
            "q": "",  // query string
            "year": null,
            "yearOptions": [],
            ...props.initialState
        };
        this.fetch = _throttle(this.fetch, 300);
    }

    handleSearchInputChange = (value) => {
        this.setState({
            q: value,
        });
    };

    handleYearChange = (year) => {
        this.setState({
            year: year
        });
    };

    componentDidMount = () => {
        const filterState = this.getFilterState(this.state);
        console.debug("CourseVideosPage: filterState", filterState);
        this.fetch();
    };

    componentWillUnmount = function () {
        this.serverRequest.abort();
    };

    componentDidUpdate(prevProps, prevState) {
        if (this.state.loading) {
            this.fetch();
        } else {
            hideBodyPreloader();
        }
    };

    getFilterState(state) {
        let {q, semester} = state;
        let filterState = {q, semester};
        Object.keys(filterState).map((k) => {
            if (k === "year" && filterState[k] !== null) {
                filterState[k] = filterState[k]["value"];
            }
            // Convert null and undefined to empty string
            filterState[k] = !filterState[k] ? "" : filterState[k];
        });
        return filterState;
    }

    fetch = (payload = null) => {
        console.debug("CourseVideosPage: fetch", this.props, payload);
        this.serverRequest = $.ajax({
            type: "GET",
            url: this.props.entry_url,
            dataType: "json",
            data: payload
        }).done((data) => {
            // Collect options for year select
            let years = new Set();
            data.forEach((item) => { years.add(item.semester.year) });
            let options = [];
            years.forEach((year) => {
               options.push({value: year, label: year});
            });
            this.setState({
                loading: false,
                items: data,
                yearOptions: options
            });
        }).fail(() => {
            showErrorNotification("Ошибка загрузки данных. Попробуйте перезагрузить страницу.");
        });
    };

    render() {
        const {q, year} = this.state;
        let filteredItems = this.state.items.filter(function(item) {
            let yearCondition = (year !== null) ? item.semester.year === year.value : true;
            return yearCondition &&
                   item.name.toLowerCase().search(q.toLowerCase()) !== -1;
        });

        return (
            <Fragment>
                <div className="row">
                    <div className="col-lg-9 order-lg-1 order-2">
                        <div className="row">
                            {filteredItems.map((course) =>
                                <div key={course.id} className="col-12 col-sm-6 col-lg-4 mb-4">
                                    <a className="card _shadowed _video"  href={`${course.url}/classes/`}>
                                        <div className="card__content">
                                            <h4 className="card__title">{ course.name }</h4>
                                            <div className="author">
                                                {course.teachers.join(", ")}
                                            </div>
                                        </div>
                                        <div className="card__content _meta">{course.semester.name}</div>
                                    </a>
                                </div>
                            )}

                            {!this.state.loading && filteredItems.length <= 0 && "Выберите другие параметры фильтрации."}
                        </div>
                    </div>

                    <div className="col-lg-3 order-lg-2 order-0">
                        <div className="ui form">
                            <div className="field">
                                <SearchInput
                                    onChange={this.handleSearchInputChange}
                                    placeholder="Название курса"
                                    value={q}
                                    icon="search"
                                />
                            </div>
                            <div className="field">
                                <Select
                                    onChange={this.handleYearChange}
                                    value={year}
                                    name="year"
                                    isClearable={true}
                                    placeholder="Год прочтения"
                                    options={this.state.yearOptions}
                                    key="year"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </Fragment>
        );
    }
}

CourseVideosPage.propTypes = {
    entry_url: PropTypes.string.isRequired
};

export default CourseVideosPage;