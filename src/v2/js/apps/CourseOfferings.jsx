import ky from 'ky';
import React, {Fragment} from 'react';
import _includes from 'lodash-es/includes';
import _partialRight from 'lodash-es/partialRight';
import _isEqual from 'lodash-es/isEqual';
import _cloneDeep from 'lodash-es/cloneDeep';
import * as PropTypes from 'prop-types';
import Media from 'react-media';

import SearchInput from 'components/SearchInput';
import {createBrowserHistory} from "history";
import {
    hideBodyPreloader,
    loadIntersectionObserverPolyfill,
    showBodyPreloader,
    showErrorNotification
} from "utils";
import {getOptionByValue, Select} from "components/Select";
import Checkbox from "components/Checkbox";
import RadioGroup from "components/RadioGroup";
import RadioOption from "components/RadioOption";
import Icon from "components/Icon";
import { Tooltip } from 'components/Tooltip';
import {
    onMultipleCheckboxFilterChange,
    onRadioFilterChange,
    onSearchInputChange,
    onSelectFilterChange,
} from "components/utils";
import {desktopMediaQuery, tabletMaxMediaQuery} from "utils/media";
import {historyPush, onPopState} from "utils/history";


export let polyfills = [
    loadIntersectionObserverPolyfill(),
];


const history = createBrowserHistory();


function FilterState(state) {
    // FIXME: Convert null and undefined to empty string?
    this.academicYear = state.academicYear;
    this.branch = state.branch;
    this.terms = state.terms;
}
FilterState.prototype.toURLSearchParams = function () {
    let params = new URLSearchParams();
    params.set('academic_year', this.academicYear.value);
    params.set('branch', this.branch.value);
    params.set('terms', this.terms.join(","));
    return params;
};


class CourseOfferings extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            "loading": true,
            "items": [],
            "filteredItems": new Set(),
            "courseNameQuery": "",
            "academicYear": null,
            "academicYearOptions": this.getYearOptions(props.initialState.branch),
            "branch": null,
            ..._cloneDeep(props.initialState)
        };
        this.latestFetchAbortController = null;
    }

    historyPush = historyPush.bind(this, history);

    getYearOptions(branchOption) {
        let academicYearOptions = [];
        const branch = getOptionByValue(this.props.branchOptions, branchOption.value);
        if (branch) {
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

    handleBranchSelectChange = onSelectFilterChange.call(this, {
        applyPatches: [
            this.checkYearOption
        ],
        setStateCallback: this.historyPush
    });

    handleBranchRadioChange = onRadioFilterChange.call(this, {
        applyPatches: [
            this.checkYearOption
        ],
        setStateCallback: this.historyPush
    });

    handleAcademicYearChange = onSelectFilterChange.call(this, {
        setStateCallback: this.historyPush
    });

    handleMultipleCheckboxChange = onMultipleCheckboxFilterChange.call(this, {
        applyPatches: [
            this.filteredItemsPatch
        ],
        setStateCallback: this.historyPush
    });

    getFilterState(state) {
        return new FilterState(state);
    }

    /**
     * Update state value if current `academicYear` is not present in
     * selected branch.
     */
    checkYearOption(state, name = 'academicYear') {
        const options = this.getYearOptions(state.branch);
        if (getOptionByValue(options, state.academicYear) === null) {
            return {[name]: options[0]};
        }
        return {};
    }

    componentDidMount = () => {
        this.fetch((new FilterState(this.state)).toURLSearchParams());
        // FIXME: Do we need ref for this?
        this.unlistenHistory = history.listen(onPopState.bind(this));
    };

    componentWillUnmount = function () {
        this.unlistenHistory();
        this.latestFetchAbortController.abort();
    };

    componentDidUpdate(prevProps, prevState, snapshot) {
        const prevFilterState = new FilterState(prevState);
        const filterState = new FilterState(this.state);
        if (this.state.loading || !_isEqual(prevFilterState, filterState)) {
            const payload = filterState.toURLSearchParams();
            this.fetch(payload);
        } else {
            hideBodyPreloader();
        }
    }

    fetch = async (urlParams = null) => {
        console.debug(`${this.constructor.name}: fetch`, this.props, urlParams);
        if (this.latestFetchAbortController !== null) {
            this.latestFetchAbortController.abort();
        }

        const abortController = new AbortController();
        this.latestFetchAbortController = abortController;

        try {
            let requests = this.props.endpoints.map(endpoint => {
                return ky.get(endpoint, {
                    searchParams: urlParams,
                    headers: {'content-type': 'application/json'},
                    signal: abortController.signal
                });
            });
            let items = [];
            let jsons = await Promise.all(requests.map(r => r.json()));
            // Abort signal was received during JSON parsing
            if (abortController.signal.aborted) {
                return;
            }
            for (const d of jsons) {
                items = items.concat(d);
            }

            items.sort((a, b) => a.name.localeCompare(b.name));
            // Sort by course title

            this.setState( (state) => {
                return {
                    loading: false,
                    items: items,
                    academicYearOptions: this.getYearOptions(state.branch),
                    filteredItems: this.filterItems(items, state)
                };
            });
        } catch(reason) {
            console.debug(`Fetch error: ${reason}`);
            if (reason.name !== 'AbortError') {
                showErrorNotification("Ошибка загрузки данных. Попробуйте перезагрузить страницу.");
            }
        }
    };

    filterItems(items, state) {
        let filteredItems = new Set();
        const {academicYear, courseNameQuery, terms} = state;
        for (const item of items) {
            let yearCondition = (academicYear !== null) ?
                item.semester.academic_year === academicYear.value :
                true;
            let semesterCondition = terms.includes(item.semester.type);
            if (yearCondition && semesterCondition &&
                _includes(item.name.toLowerCase(), courseNameQuery.toLowerCase())) {
                filteredItems.add(item.id);
            }
        }
        return filteredItems;
    }

    filteredItemsPatch(state, name = 'filteredItems') {
        return {[name]: this.filterItems(state.items, state)};
    }

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
            terms,
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
                        <div className="card border-xs-0 mb-4">
                            <div className="card__content _big _courses-filter">
                                <h1>Курсы центра</h1>
                                <form className="ui form">
                                    <div className="row">
                                        <div className="field col-lg-9 mb-3 mb-lg-0">
                                            <label className='h4 d-lg-none'>Название курса</label>
                                            <SearchInput
                                                debounceMaxWait={100}
                                                handleSearch={this.handleSearchInputChange}
                                                name="courseNameQuery"
                                                query={courseNameQuery}
                                                placeholder="Поиск по названию курса"
                                                icon="search"
                                            />
                                        </div>
                                        <Media query={tabletMaxMediaQuery} render={() =>
                                            (
                                                <Fragment>
                                                    <div className="field col-12 mb-3">
                                                        <label className='h4' htmlFor="">Отделение</label>
                                                        <div className="ui select">
                                                            <Select
                                                                onChange={this.handleBranchSelectChange}
                                                                value={branch}
                                                                name="branch"
                                                                isClearable={false}
                                                                placeholder="Отделение"
                                                                options={branchOptions}
                                                            />
                                                        </div>
                                                    </div>
                                                    <div className="field col-12 mb-3">
                                                        <label className='h4' htmlFor="">Учебный год</label>
                                                        <div className="ui select">
                                                            <Select
                                                                onChange={this.handleAcademicYearChange}
                                                                value={academicYear}
                                                                name="academicYear"
                                                                isClearable={false}
                                                                placeholder="Учебный год"
                                                                options={academicYearOptions}
                                                                key="year"
                                                            />
                                                        </div>
                                                    </div>
                                                    <div className="field col-12 mb-3">
                                                        <label className='h4'>Семестр</label>
                                                        <div className="grouped">
                                                            {semesterOptions.map((option) =>
                                                                <Checkbox
                                                                    name="terms"
                                                                    key={option.value}
                                                                    value={option.value}
                                                                    checked={terms.includes(option.value)}
                                                                    onChange={this.handleMultipleCheckboxChange}
                                                                    label={option.label}
                                                                />
                                                            )}
                                                        </div>
                                                    </div>
                                                </Fragment>
                                            )}
                                        />
                                    </div>
                                </form>
                            </div>
                            <div className={`card__content p-0`}>
                                {
                                    !this.state.loading &&
                                    <CourseList items={items} filteredItems={filteredItems} />
                                }
                            </div>
                            {
                                !this.state.loading && filteredItems.size <= 0
                                    ? <div className="card__content _big pt-md-0">Выберите другие параметры фильтрации.</div>
                                    : ""
                            }
                        </div>
                    </div>
                    <Media query={desktopMediaQuery} render={() => (
                        <div className="col-lg-3">
                            <form
                                className="ui form px-6 mt-6 mt-lg-10 ml-lg-4">
                                <div className="field">
                                    <label className='h4'>Отделение</label>
                                    <RadioGroup name="branch"
                                                required
                                                onChange={this.handleBranchRadioChange}
                                                value={`branch-${branch.value}`}>
                                        {branchOptions.map((item) =>
                                            <RadioOption key={item.value}
                                                         id={`branch-${item.value}`}
                                                         value={item.value}>
                                                {item.label}
                                            </RadioOption>
                                        )}
                                    </RadioGroup>
                                </div>
                                <div className="field">
                                    <label className='h4' htmlFor="">Учебный год</label>
                                    <div className="ui select">
                                        <Select
                                            onChange={this.handleAcademicYearChange}
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
                                                name="terms"
                                                key={option.value}
                                                value={option.value}
                                                checked={terms.includes(option.value)}
                                                onChange={this.handleMultipleCheckboxChange}
                                                label={option.label}
                                            />
                                        )}
                                    </div>
                                </div>
                            </form>
                        </div>
                    )}
                    />
                </div>
            </Fragment>
        );
    }
}

const courseType = PropTypes.shape({
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
});

const propTypes = {
    endpoints: PropTypes.arrayOf(PropTypes.string).isRequired,
    // history api depends on initial state
    initialState: PropTypes.shape({
        branch: PropTypes.shape({
            value: PropTypes.string.isRequired,
            label: PropTypes.string.isRequired,
            established: PropTypes.number.isRequired,
        }).isRequired,
        academicYear: PropTypes.shape({
            value: PropTypes.number.isRequired,
            label: PropTypes.string.isRequired
        }).isRequired,
        terms: PropTypes.arrayOf(PropTypes.string).isRequired,
    }).isRequired,
    currentYear: PropTypes.number.isRequired,
    branchOptions: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired,
        established: PropTypes.number.isRequired,
    })).isRequired,
    semesterOptions: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired
    })).isRequired,
    courses: PropTypes.arrayOf(courseType),
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
                    .filter(function(item) {return filteredItems.has(item.id);})
                    .map(item =>
                    <div className="table__row" key={`course-${item.id}`}>
                        <div className="table__cell">
                            {item.branch.is_club ? <ClubIcon/> : ''}<a href={item.url} className="__course">{item.name}</a>
                        </div>
                        <div className="table__cell _teachers">
                            {item.teachers.map((teacher, i, arr) =>
                                <Fragment key={`teacher-${teacher.id}`}>
                                    <a href={`/teachers/${teacher.id}/`}>{teacher.name}</a>{arr.length - 1 !== i ? ", " : ""}
                                </Fragment>
                            )}
                        </div>
                        <div className="table__cell _icons">
                            {item.materials.video ? <VideoIcon key={'video-icon'}/> : ""}
                            {item.materials.slides ? <SlidesIcon key={'slides-icon'}/> : ""}
                            {item.materials.files ? <FilesIcon key={'files-icon'}/> : ""}
                        </div>
                    </div>
                )}
            </div>
        );
    }
}

CourseList.propTypes = {
    className: PropTypes.string,
    items: PropTypes.arrayOf(courseType),
    filteredItems: PropTypes.instanceOf(Set)
};


const ClubIcon = () => (
    <Tooltip title="Курс CS клуба"><Icon id={'cs-club'} className={`mr-1`}/></Tooltip>
);

const VideoIcon = () => (
    <Tooltip title="Видео"><Icon id={'video'} className={'mr-1'}/></Tooltip>
);

const SlidesIcon = () => (
    <Tooltip title="Слайды"><Icon id={'slides'} className={'mr-1'}/></Tooltip>
);

const FilesIcon = () => (<Tooltip title="Файлы"><Icon id={'files'}/></Tooltip>);
