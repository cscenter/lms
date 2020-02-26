import React, {Fragment} from 'react';
import * as PropTypes from 'prop-types';
import {withTranslation} from 'react-i18next';
import i18next from 'i18next';

import _throttle from 'lodash-es/throttle';
import $ from 'jquery';

import {Select} from 'components/Select';
import UserCardList from 'components/UserCardList';
import {
    hideBodyPreloader,
    loadIntersectionObserverPolyfill,
    showBodyPreloader,
    showErrorNotification
} from "../utils";
import {onSelectChange} from "components/utils";
import {optionIntType} from "types/props";

export let polyfills = [
    loadIntersectionObserverPolyfill(),
];


class Alumni extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            "loading": true,
            "items": [],
            ...props.initialState
        };
        this.fetch = _throttle(this.fetch, 300);
    }

    handleSelectChange = onSelectChange.bind(this);

    componentDidMount() {
        const filterState = this.getFilterState(this.state);
        console.debug("Alumni: filterState", filterState);
        const newPayload = this.getRequestPayload(filterState);
        console.debug("Alumni: newPayload", newPayload);
        this.fetch(newPayload);
    }

    componentWillUnmount() {
        this.serverRequest.abort();
    }

    componentDidUpdate(prevProps, prevState, snapshot) {
        if (this.state.loading) {
            const filterState = this.getFilterState(this.state);
            const newPayload = this.getRequestPayload(filterState);
            this.fetch(newPayload);
        } else {
            hideBodyPreloader();
        }
    }

    getFilterState(state) {
        let {year, branch} = state;
        return {year, branch};
    }

    getRequestPayload(filterState) {
        Object.keys(filterState).map((k) => {
            if (k === "year") {
                filterState[k] = filterState[k]["value"];
            }
            // Convert null and undefined to empty string
            filterState[k] = !filterState[k] ? "" : filterState[k];
        });
        return filterState;
    }

    fetch = (payload) => {
        console.debug("Alumni: fetch", this.props, payload);
        this.serverRequest = $.ajax({
            type: "GET",
            url: this.props.endpoint,
            dataType: "json",
            data: payload
        }).done((result) => {
            result.data.forEach((g) => {
                g.url = `/students/${g.student.id}/`;
                g.name = `${g.student.name} ${g.student.surname}`;
            });
            this.setState({
                loading: false,
                items: result.data,
            });
        }).fail(() => {
            showErrorNotification("Ошибка загрузки данных. Попробуйте перезагрузить страницу.");
        });
    };

    render() {
        if (this.state.loading) {
            showBodyPreloader();
        }
        const {year, branch, area} = this.state;
        const {yearOptions, branchOptions, areaOptions} = this.props;

        let filteredItems = this.state.items.filter(function(item) {
            let branchCondition = (branch !== null) ? item.student.branch === branch.value : true;
            let areaCondition = (area !== null) ? item.areas.includes(area.value) : true;
            let yearCondition = (year !== null) ? item.year === year.value : true;
            return branchCondition && areaCondition && yearCondition;
        });

        return (
            <Fragment>
                <h1>Выпускники</h1>
                <div className="row mb-4">
                    <div className="col-lg-2 mb-4">
                        <Select
                            onChange={this.handleSelectChange}
                            value={year}
                            name="year"
                            isClearable={false}
                            placeholder="Год выпуска"
                            options={yearOptions}
                            key="year"
                        />
                    </div>
                    <div className="col-lg-3 mb-4">
                        <Select
                            onChange={this.handleSelectChange}
                            value={area}
                            name="area"
                            placeholder={i18next.t("Направление")}
                            isClearable={true}
                            options={areaOptions}
                            key="area"
                        />
                    </div>
                    <div className="col-lg-3 mb-4">
                        <Select
                            onChange={this.handleSelectChange}
                            value={branch}
                            name="branch"
                            isClearable={true}
                            placeholder={i18next.t("Город")}
                            options={branchOptions}
                            key="branch"
                        />
                    </div>
                </div>
                {
                    filteredItems.length > 0 ?
                        <UserCardList users={filteredItems} />
                        : i18next.t("Таких выпускников у нас нет. Выберите другие параметры фильтрации.")
                }
            </Fragment>
        );
    }
}

const propTypes = {
    initialState: PropTypes.shape({
        year: optionIntType.isRequired,
        area: PropTypes.shape({
            value: PropTypes.string.isRequired,
            label: PropTypes.string.isRequired
        }),
        branch: PropTypes.string,
    }).isRequired,
    endpoint: PropTypes.string.isRequired,
    branchOptions: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired
    })).isRequired,
    areaOptions: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.string.isRequired,
        label: PropTypes.string.isRequired
    })).isRequired,
    yearOptions: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.number.isRequired,
        label: PropTypes.string.isRequired
    })).isRequired,
};

Alumni.propTypes = propTypes;

export default withTranslation()(Alumni);
