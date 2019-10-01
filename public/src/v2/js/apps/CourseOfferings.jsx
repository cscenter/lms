import React, {Fragment} from 'react';

import _includes from 'lodash-es/includes';
import _partialRight from 'lodash-es/partialRight';
import $ from 'jquery';
import * as PropTypes from 'prop-types';
import SearchInput from 'components/SearchInput';
import {
    hideBodyPreloader,
    loadIntersectionObserverPolyfill, showBodyPreloader,
    showErrorNotification
} from "utils";
import Select from "components/Select";
import Checkbox from "components/Checkbox";
import RadioGroup from "components/RadioGroup";
import RadioOption from "components/RadioOption";
import Icon from "components/Icon";
import {
    onInputChange,
    onMultipleCheckboxChange,
    onSearchInputChange,
    onSelectChange
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
            "filteredItems": new Set(),
            "courseNameQuery": "",
            "academicYear": null,
            "academicYearOptions": this.getYearOptions(props.initialState.branch),
            "branch": null,
            "semesters": semesters,
            ...props.initialState
        };
    }

    getYearOptions(branchName) {
        let academicYearOptions = [];
        const branch = this.props.branchOptions.find((option) => {
            if (option.value === branchName) {
                return option;
            }
        });
        if (branch !== undefined) {
            for (let y = this.props.currentYear; y >= branch.established; --y) {
                academicYearOptions.push({value: y, label: `${y}/${y + 1}`});
            }
        }
        return academicYearOptions;
    }

    handleSearchInputChange = _partialRight(
        onSearchInputChange,
        {applyPatch: this.filteredItemsPatch.bind(this)}
    ).bind(this);

    handleInputChange = _partialRight(
        onInputChange,
        {applyPatch: this.checkYearOption.bind(this)}
    ).bind(this);

    handleSelectChange = onSelectChange.bind(this);

    handleMultipleCheckboxChange = _partialRight(
        onMultipleCheckboxChange,
        {applyPatch: this.filteredItemsPatch.bind(this)}
    ).bind(this);

    /**
     * Update state value if current `academicYear` is not present in
     * selected branch.
     */
    checkYearOption(state, name = 'academicYear') {
        const options = this.getYearOptions(state.branch);
        // FIXME: compare by values!
        console.log(options, state.academicYear, options.includes(state.academicYear));
        if (!options.includes(state.academicYear)) {
            return {[name]: options[0]}
        }
        return {}
    }

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
        if (this.state.loading || prevState.academicYear !== this.state.academicYear || prevState.branch !== this.state.branch) {
            const payload = this.getRequestPayload(this.state);
            this.fetch(payload);
        } else {
            hideBodyPreloader();
        }
    }

    getRequestPayload(state) {
        // FIXME: Convert null and undefined to empty string
        return {
            'academic_year': state.academicYear.value,
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
                let items = [];
                let years = new Set();
                for (const d of iterables) {
                    items = items.concat(d);
                }
                this.setState( (state) => {
                    return {
                        loading: false,
                        items: items,
                        academicYearOptions: this.getYearOptions(state.branch),
                        filteredItems: this.filterItems(items, state)
                    };
                });
            }).catch((reason) => {
            showErrorNotification("Ошибка загрузки данных. Попробуйте перезагрузить страницу.");
        });
    };

    filterItems(items, state) {
        let filteredItems = new Set();
        const {academicYear, courseNameQuery, semesters} = state;
        for (const item of items) {
            let yearCondition = (academicYear !== null) ?
                item.semester.academic_year === academicYear.value :
                true;
            let semesterCondition = semesters.includes(item.semester.type);
            if (yearCondition && semesterCondition &&
                _includes(item.name.toLowerCase(), courseNameQuery.toLowerCase())) {
                filteredItems.add(item.id);
            }
        }
        return filteredItems;
    }

    filteredItemsPatch(state, name = 'filteredItems') {
        return {[name]: this.filterItems(state.items, state)}
    };

    render() {
        const {
            branchOptions,
            semesterOptions,
        } = this.props;
        const {
            academicYearOptions,
            courseNameQuery,
            academicYear,
            branch,
            semesters,
            items,
            filteredItems
        } = this.state;

        if (this.state.loading) {
            showBodyPreloader();
        }

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
                            <div className={`card__content p-0`}>
                                {
                                    !this.state.loading &&
                                    <CourseList items={items} filteredItems={filteredItems} />
                                }
                            </div>
                            {
                                !this.state.loading && filteredItems.size <= 0
                                    ? <div className="card__content _big pt-0">Выберите другие параметры фильтрации.</div>
                                    : ""
                            }
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
                                    <label className='h4' htmlFor="">Учебный год</label>
                                    <Select
                                        onChange={this.handleSelectChange}
                                        value={academicYear}
                                        name="academicYear"
                                        isClearable={false}
                                        placeholder="Учебный год"
                                        options={academicYearOptions}
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
        label: PropTypes.string.isRequired,
        established: PropTypes.number.isRequired,
    })).isRequired,
    semesterOptions: PropTypes.arrayOf(PropTypes.shape({
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
            academic_year: PropTypes.number.isRequired,
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
        const {className, items, filteredItems} = this.props;
        if (filteredItems.size <= 0) {
            return "";
        }
        return (
            <div className={className}>
                <div className="table__row _head">
                    <div className="table__cell">Название</div>
                    <div className="table__cell">Преподаватели</div>
                    <div className="table__cell">Материалы</div>
                </div>
                {items
                    .filter(function(item) {return filteredItems.has(item.id)})
                    .map(item =>
                    <div className="table__row" key={`course-${item.id}`}>
                        <div className="table__cell">
                            <a href={item.url}
                               className="__course">{item.name}</a>
                        </div>
                        <div className="table__cell _teachers">
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
