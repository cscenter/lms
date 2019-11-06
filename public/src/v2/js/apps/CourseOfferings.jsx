import ky from 'ky';
import React, {Fragment} from 'react';
import _includes from 'lodash-es/includes';
import _partialRight from 'lodash-es/partialRight';
import _isEqual from 'lodash-es/isEqual';
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
    onMultipleCheckboxChange,
    onRadioFilterChange,
    onSearchInputChange,
    onSelectFilterChange,
} from "components/utils";
import {desktopMediaQuery, tabletMaxMediaQuery} from "utils/media";


export let polyfills = [
    loadIntersectionObserverPolyfill(),
];


const history = createBrowserHistory();


function FilterState(state) {
    // FIXME: Convert null and undefined to empty string
    this.academicYear = state.academicYear;
    this.branch = state.branch;
}
FilterState.prototype.getPayload = function () {
    return {
        'academic_year': this.academicYear.value,
        'branch': this.branch.value,
    };
};


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
        this.latestFetchAbortController = null;
    }

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

    handleMultipleCheckboxChange = _partialRight(
        onMultipleCheckboxChange,
        {applyPatch: this.filteredItemsPatch.bind(this)}
    ).bind(this);

    getHistoryState(location, initialState) {
        if (!location.state) {
            return new FilterState(initialState);
        } else {
            return new FilterState(location.state);
        }
    }

    /**
     * Push new browser history if filterState was updated
     */
    historyPush() {
        const filterState = new FilterState(this.state);
        const payload = filterState.getPayload();
        const historyState = this.getHistoryState(history.location,
                                                  this.props.initialState);
        if (!_isEqual(filterState, historyState)) {
            console.debug(`History.push: new filter state `, JSON.stringify(filterState));
            history.push({
                pathname: history.location.pathname,
                search: `?branch=${payload.branch}&academic_year=${payload.academic_year}`,
                state: filterState
            });
        }
    }

    /**
     * Update state value if current `academicYear` is not present in
     * selected branch.
     */
    checkYearOption(state, name = 'academicYear') {
        const options = this.getYearOptions(state.branch);
        if (getOptionByValue(options, state.academicYear) === null) {
            return {[name]: options[0]}
        }
        return {}
    }

    componentDidMount = () => {
        this.fetch((new FilterState(this.state)).getPayload());
        // FIXME: Do we need ref for this?
        this.unlistenHistory = history.listen((location, action) => {
            const currentState = new FilterState(this.state);
            const historyState = this.getHistoryState(location,
                                                      this.props.initialState);
            console.debug('History.listen: current state', JSON.stringify(currentState));
            console.debug('History.listen: history state', JSON.stringify(historyState));
            if (!_isEqual(currentState, historyState)) {
                console.debug(`History.listen: new state`, JSON.stringify(historyState));
                this.setState(historyState);
            }
        });
    };

    componentWillUnmount = function () {
        this.unlistenHistory();
        if (this.requests) {
            for (const request of this.requests) {
                request.abort();
            }
        }
    };

    componentDidUpdate(prevProps, prevState, snapshot) {
        const prevFilterState = new FilterState(prevState);
        const filterState = new FilterState(this.state);
        if (this.state.loading || !_isEqual(prevFilterState, filterState)) {
            const payload = filterState.getPayload();
            this.fetch(payload);
        } else {
            hideBodyPreloader();
        }
    }

    fetch = async (payload = null) => {
        console.debug(`${this.constructor.name}: fetch`, this.props, payload);
        if (this.latestFetchAbortController !== null) {
            this.latestFetchAbortController.abort();
        }

        const abortController = new AbortController();
        this.latestFetchAbortController = abortController;
        this.requests = this.props.entryURL.map(entryURL => {
            return ky.get(entryURL, {
                searchParams: payload,
                headers: {'content-type': 'application/json'},
                signal: abortController.signal
            })
        });

        try {
            let responses = await Promise.all(this.requests);
            let items = [];
            let jsons = await Promise.all(responses.map(r => r.json()));
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
            showErrorNotification("Ошибка загрузки данных. Попробуйте перезагрузить страницу.");
        }
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
                                    <RadioGroup required name="branch"
                                                className=""
                                                onChange={this.handleBranchRadioChange}
                                                selected={`branch-${branch.value}`}>
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
                    )}
                    />
                </div>
            </Fragment>
        );
    }
}

const propTypes = {
    entryURL: PropTypes.arrayOf(PropTypes.string).isRequired,
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
        }).isRequired
    }).isRequired,
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
                            <a href={item.url} className="__course">{item.name}</a>&nbsp;{item.branch.is_club ? <ClubIcon/> : ''}
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


const ClubIcon = () => (
    <Tooltip title="Курс CS клуба"><Icon id={'cs-club'} className={`ml-1`}/></Tooltip>
);

const VideoIcon = () => (
    <Tooltip title="Видео"><Icon id={'video'} className={'mr-1'}/></Tooltip>
);

const SlidesIcon = () => (
    <Tooltip title="Слайды"><Icon id={'slides'} className={'mr-1'}/></Tooltip>
);

const FilesIcon = () => (<Tooltip title="Файлы"><Icon id={'files'}/></Tooltip>);
