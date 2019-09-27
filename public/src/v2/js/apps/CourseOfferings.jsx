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
import Select from "components/Select";
import Checkbox from "components/Checkbox";
import RadioGroup from "components/RadioGroup";
import RadioOption from "components/RadioOption";
import Icon from "components/Icon";
import {
    onMultipleCheckboxChange,
    onSearchInputChange,
    onInputChangeLoading,
    onSelectChangeLoading
} from "components/utils";


export let polyfills = [
    loadIntersectionObserverPolyfill(),
];


class CourseOfferings extends React.Component {

    constructor(props) {
        super(props);
        // Select all terms by default, could be overridden by initial state
        let semesters = [];
        for (const s of props.semesterOptions) {
            semesters.push(s.value);
        }
        this.state = {
            "loading": true,
            "items": [],
            "courseNameQuery": "",
            "year": null,
            "branch": null,
            "semesters": semesters,
            "academicDisciplines": [],
            ...props.initialState
        };
        this.fetch = _throttle(this.fetch, 300);
    }

    handleInputChange = onInputChangeLoading.bind(this);

    handleSearchInputChange = onSearchInputChange.bind(this);

    handleSelectChange = onSelectChangeLoading.bind(this);


    /**
     * Handle state for multiple checkboxes with the same name
     * @param event
     */
    handleMultipleCheckboxChange = onMultipleCheckboxChange.bind(this);

    componentDidMount = () => {
        const payload = this.getRequestPayload(this.state);
        this.fetch(payload);
    };

    componentWillUnmount = function () {
        if (this.requests) {
            for (const request of this.requests) {
                request.abort();
            }
        }
    };

    componentDidUpdate(prevProps, prevState, snapshot) {
        if (this.state.loading || prevState.year !== this.state.year || prevState.branch !== this.state.branch) {
            const payload = this.getRequestPayload(this.state);
            this.fetch(payload);
        } else {
            hideBodyPreloader();
        }
    }

    getRequestPayload(state) {
        // FIXME: Convert null and undefined to empty string
        return {
            'year': state.year.value,
            'branch': state.branch,
        };
    }

    fetch = (payload = null) => {
        console.debug(`${this.constructor.name}: fetch`, this.props, payload);
        this.requests = this.props.entryURL.map(entryURL => $.ajax({
            type: "GET",
            url: entryURL,
            dataType: "json",
            data: payload
        }));

        Promise.all(this.requests)
            .then((iterables) => {
                let data = [];
                for (const d of iterables) {
                    data = data.concat(d);
                }
                this.setState({
                    loading: false,
                    items: data,
                });
            }).catch((reason) => {
            showErrorNotification("Ошибка загрузки данных. Попробуйте перезагрузить страницу.");
        });
    };

    render() {
        const {
            courseNameQuery,
            year,
            branch,
            academicDisciplines,
            semesters,
            items
        } = this.state;
        const {
            branchOptions,
            yearOptions,
            semesterOptions,
            academicDisciplinesOptions
        } = this.props;
        let filteredItems = items.filter(function (item) {
            let yearCondition = (year !== null) ? item.semester.year === year.value : true;
            let semesterCondition = semesters.includes(item.semester.type);
            return yearCondition && semesterCondition &&
                _includes(item.name.toLowerCase(), courseNameQuery.toLowerCase());
        });

        return (
            <Fragment>
                <div className="row no-gutters">
                    <div className="col-lg-9">
                        <div className="card">
                            <div className="card__content _big">
                                <h1>Курсы центра</h1>
                                <div className="row">
                                    <div className="field col-lg-9 mb-3 mb-lg-0">
                                        <SearchInput
                                            handleSearch={this.handleSearchInputChange}
                                            name="courseNameQuery"
                                            query={courseNameQuery}
                                            placeholder="Поиск по названию курса"
                                            icon="search"
                                        />
                                    </div>
                                </div>
                            </div>
                            <div className="card__content p-0">
                                {
                                    !this.state.loading && filteredItems.length > 0 &&
                                        <div className="card__content p-0">
                                            <CourseList items={filteredItems} />
                                        </div>
                                }
                                {
                                    !this.state.loading && filteredItems.length <= 0
                                        ? <div className="card__content _big pt-0">Выберите другие параметры фильтрации.</div>
                                        : ""
                                }
                            </div>
                        </div>
                    </div>

                    <div className="col-lg-3">
                        <form className="ui form pl-6 mt-10 ml-lg-4 d-none d-lg-block">
                            <div className="field">
                                <label className='h4'>Отделение</label>
                                <RadioGroup required name="branch" className="" onChange={this.handleInputChange} selected={`branch-${branch}`}>
                                    {branchOptions.map((item) =>
                                        <RadioOption  key={item.value} id={`branch-${item.value}`} value={item.value}>
                                            {item.label}
                                        </RadioOption>
                                    )}
                                </RadioGroup>
                            </div>
                            <div className="field">
                                <div className="ui select">
                                    <label className='h4' htmlFor="">Год</label>
                                    <Select
                                        onChange={this.handleSelectChange}
                                        value={year}
                                        name="year"
                                        isClearable={false}
                                        placeholder="Год прочтения"
                                        options={yearOptions}
                                        key="year"
                                    />
                                </div>
                            </div>
                            <div className="field">
                                <label className='h4'>Семестр</label>
                                <div className="grouped">
                                    {semesterOptions.map((option) =>
                                        <Checkbox
                                            name="semesters"
                                            key={option.value}
                                            value={option.value}
                                            checked={semesters.includes(option.value)}
                                            onChange={this.handleMultipleCheckboxChange}
                                            label={option.label}
                                        />
                                    )}
                                </div>
                            </div>
                            <div className="field">
                                <label className='h4'>Базовые курсы программ</label>
                                <div className="grouped">
                                    {academicDisciplinesOptions.map((option) =>
                                        <Checkbox
                                            name="academicDisciplines"
                                            key={option.value}
                                            value={option.value}
                                            checked={academicDisciplines.includes(option.value)}
                                            onChange={this.handleMultipleCheckboxChange}
                                            label={option.label}
                                        />
                                    )}
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            </Fragment>
        );
    }
}

const propTypes = {
    entryURL: PropTypes.arrayOf(PropTypes.string).isRequired,
    branchOptions: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired
    })).isRequired,
    yearOptions: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.number.isRequired,
        label: PropTypes.string.isRequired
    })).isRequired,
    semesterOptions: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired
    })).isRequired,
    academicDisciplinesOptions: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired
    })).isRequired,
    courses: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.number.isRequired,
        name: PropTypes.string.isRequired,
        url: PropTypes.string.isRequired,
        teachers: PropTypes.arrayOf(PropTypes.shape({
            id: PropTypes.number.isRequired,
            name: PropTypes.string.isRequired
        })).isRequired,
        branch: PropTypes.shape({
            id: PropTypes.number.isRequired,
            code: PropTypes.string.isRequired
        }).isRequired,
        semester: PropTypes.shape({
            id: PropTypes.number.isRequired,
            index: PropTypes.number.isRequired,
            year: PropTypes.number.isRequired,
            type: PropTypes.oneOf(['autumn', 'spring']).isRequired,
        }).isRequired,
        materials: PropTypes.shape({
            video: PropTypes.bool.isRequired,
            slides: PropTypes.bool.isRequired,
            files: PropTypes.bool.isRequired,
        }).isRequired
    })),
};

CourseOfferings.propTypes = propTypes;

export default CourseOfferings;


class CourseList extends React.Component {
    static defaultProps = {
        className: 'table _mobile _courses'
    };

    render() {
        const {className, items} = this.props;
        return (
            <div className={className}>
                <div className="table__row _head">
                    <div className="table__cell">Название</div>
                    <div className="table__cell">Преподаватели</div>
                    <div className="table__cell">Материалы</div>
                </div>
                {items.map(item =>
                    <div className="table__row" key={`course-${item.id}`}>
                        <div className="table__cell">
                            <a href={item.url}
                               className="__course">{item.name}</a>
                        </div>
                        <div className="table__cell">
                            {item.teachers.map((teacher, i, arr) =>
                                <Fragment key={`teacher-${teacher.id}`}>
                                    <a href={`/teachers/${teacher.id}/`}>{teacher.name}</a>{arr.length - 1 !== i ? ", " : ""}
                                </Fragment>
                            )}
                        </div>
                        <div className="table__cell">
                            {item.materials.video ? <Icon
                                id={'video'}/> : ""} {item.materials.slides ?
                            <Icon id={'slides'}/> : ""} {item.materials.files ?
                            <Icon id={'files'}/> : ""}
                        </div>
                    </div>
                )}
            </div>
        );
    }
}
