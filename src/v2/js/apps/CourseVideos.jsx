import React, {Fragment} from 'react';

import _throttle from 'lodash-es/throttle';
import _includes from 'lodash-es/includes';
import $ from 'jquery';
import * as PropTypes from 'prop-types';
import SearchInput from 'components/SearchInput';
import {
    hideBodyPreloader,
    loadIntersectionObserverPolyfill,
    showErrorNotification
} from "utils";
import Select from "../components/Select";
import LazyImage from "../components/LazyImage";
import Checkbox from "../components/Checkbox";


export let polyfills = [
    loadIntersectionObserverPolyfill(),
];


class CourseVideosPage extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            "loading": true,
            "items": [],
            "q": "",  // query string
            "year": null,
            "yearOptions": [],
            "videoTypes": [],
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

    // FIXME: Duplicated. Move to utility method?
    /**
     * Handle state for multiple checkboxes with the same name
     * @param event
     */
    handleMultipleCheckboxChange = (event) => {
        const {name, value} = event.target;
        let selectedCheckboxes = this.state[name] || [];
        if (event.target.checked === true) {
            selectedCheckboxes.push(value);
        } else {
            let valueIndex = selectedCheckboxes.indexOf(value);
            selectedCheckboxes.splice(valueIndex, 1);
        }
        this.setState({
            [name]: selectedCheckboxes
        });
    };

    componentDidMount = () => {
        const filterState = this.getFilterState(this.state);
        console.debug("CourseVideosPage: filterState", filterState);
        this.fetch();
    };

    componentWillUnmount = function () {
        if (this.requests) {
            for (const request of this.requests) {
                request.abort();
            }
        }
    };

    componentDidUpdate(prevProps, prevState, snapshot) {
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
        this.requests = this.props.entry_url.map(entryURL => $.ajax({
            type: "GET",
            url: entryURL,
            dataType: "json",
            data: payload
        }));

        Promise.all(this.requests)
            .then((iterables) => {
                let data = [];
                // Aggregate data for year select
                let years = new Set();
                for (const d of iterables) {
                    data = data.concat(d);
                    d.forEach((item) => {
                        years.add(item.year)
                    });
                }
                let yearOptions = Array.from(years, year => ({
                    value: year, label: year
                }));
                yearOptions.sort((a, b) => b.value - a.value);
                data.sort((a, b) => b.year - a.year);
                this.setState({
                    loading: false,
                    items: data,
                    yearOptions: yearOptions
                });
            }).catch((reason) => {
            showErrorNotification("Ошибка загрузки данных. Попробуйте перезагрузить страницу.");
        });
    };

    getLabelColor(videoType) {
        if (videoType === "course") {
            return "_blue"
        } else if (videoType === "lecture") {
            return "_green"
        } else {
            return ""
        }
    }

    getVideoTypeLabel(videoType) {
        for (const x of this.props.videoTypes) {
            if (x.value === videoType) {
                return x.label
            }
        }
        return ""
    }

    render() {
        const {q, year, videoTypes} = this.state;
        let filteredItems = this.state.items.filter(function (item) {
            let yearCondition = (year !== null) ? item.year === year.value : true;
            let videoTypesCondition = videoTypes.includes(item.type);
            return yearCondition && videoTypesCondition &&
                _includes(item.name.toLowerCase(), q.toLowerCase());
        });

        return (
            <Fragment>
                <div className="row">
                    <div className="col-lg-9 order-lg-1 order-2">
                        <div className="card-deck _three">
                            {filteredItems.map((videoRecord) =>
                                <a key={`${videoRecord.type}_${videoRecord.id}`}
                                   className="card _shadowed _video"
                                   href={videoRecord.url}>
                                    {videoRecord.preview_url ?
                                        <LazyImage src={videoRecord.preview_url}
                                                   alt={videoRecord.name}
                                                   className={`card__img lazy-wrapper`}/>
                                        : ""
                                    }
                                    <div className="card__content">
                                        <h4 className="card__title">{videoRecord.name}</h4>
                                        <div className="author">
                                            {videoRecord.speakers.join(", ")}
                                        </div>
                                    </div>
                                    <div className="card__content _meta">
                                        <div className="ui labels circular">
                                            <span className="ui label _gray">{videoRecord.year}</span>
                                            <span className={`ui label ${this.getLabelColor(videoRecord.type)}`}>{this.getVideoTypeLabel(videoRecord.type)}</span>
                                        </div>
                                    </div>
                                </a>
                            )}
                        </div>
                        {!this.state.loading && filteredItems.length <= 0 && "Выберите другие параметры фильтрации."}
                    </div>

                    <div className="col-lg-3 order-lg-2 order-0">
                        <div className="ui form">
                            <div className="field">
                                <SearchInput
                                    handleSearch={this.handleSearchInputChange}
                                    query={q}
                                    placeholder="Название курса"
                                    icon="search"
                                />
                            </div>
                            <div className="field mb-2">
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
                            <div className="field">
                                <div className="grouped inline">
                                    {this.props.videoTypes.map((item) =>
                                        <Checkbox
                                            name="videoTypes"
                                            key={item.value}
                                            value={item.value}
                                            defaultChecked={true}
                                            onChange={this.handleMultipleCheckboxChange}
                                            label={item.label}
                                        />
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </Fragment>
        );
    }
}

const propTypes = {
    entry_url: PropTypes.arrayOf(PropTypes.string).isRequired,
    videoTypes: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired
    })),
    items: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.number.isRequired,
        name: PropTypes.string.isRequired,
        url: PropTypes.string.isRequired,
        preview_url: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['course', 'lecture']).isRequired,
        year: PropTypes.number.isRequired,
        speakers: PropTypes.arrayOf(PropTypes.string).isRequired
    })),
};

CourseVideosPage.propTypes = propTypes;

export default CourseVideosPage;