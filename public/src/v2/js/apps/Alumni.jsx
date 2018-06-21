import React, {Fragment} from 'react';
import { forceCheck } from 'react-lazyload';

import _debounce from 'lodash-es/debounce';
import $ from 'jquery';

import FormSelect from 'components/FormSelect';
import SearchInput from 'components/SearchInput';
import UserCardList from 'components/UserCardList';


// TODO: replace with HOC `UserCardFilter`
class Alumni extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            "loading": true,
            "items": [],
        };
        this.fetch = _debounce(this._fetch, 300);
    }

    handleSearchInputChange = (value) => {
        this.setState({
            query: value,
        });
    };

    handleYearChange = (year) => {
        this.setState({
            year: year
        });
    };

    handleAreaChange = (areaCode) => {
        this.setState({
            area: areaCode
        });
    };

    handleCityChange = (city) => {
        this.setState({
            city: city
        });
    };

    componentDidMount = () => {
        // Set initial state and fetch data
        // TODO: move to constructor?
        this.setState(this.props.init.state);
    };

    componentWillUnmount = function () {
        this.serverRequest.abort();
    };

    componentDidUpdate = (prevProps, prevState) => {
        if (prevState.items.length === 0) {
            const filterState = this.getFilterState(this.state);
            const newPayload = this.getRequestPayload(filterState);
            this._fetch(newPayload);
        } else {
            forceCheck();
        }
    };

    getFilterState(state) {
        let {year, city, query} = state;
        return {year, city, query};
    }

    getRequestPayload(filterState) {
        let {query, ...payload} = filterState;
        return payload;
    }

    _fetch = (payload) => {
        this.serverRequest = $.ajax({
            type: "GET",
            url: this.props.init.entry_url,
            dataType: "json"
        }).done((result) => {
            this.setState({
                loading: false,
                items: result.data,
            });
        });

    };

    render() {
        //TODO: prevent rerendering if query < 3 symbols
        const {year, city, query, area} = this.state;
        const {years, cities, areas} = this.props.init.options;

        let filteredItems = this.state.items.filter(function(item) {
            let cityCondition = (city !== null) ? item.city === city.value : true;
            let areaCondition = (area !== null) ? item.areas.includes(area.value) : true;
            let yearCondition = (year !== null) ? item.year === year.value : true;
            return  cityCondition &&  areaCondition && yearCondition &&
                    item.name.toLowerCase().search(query.toLowerCase()) !== -1;
        });

        return (
            <div className={this.state.loading ? "_loading" : ""}>
                <div className="row mb-4">
                    <div className="col-lg-3">
                        <SearchInput
                            onChange={this.handleSearchInputChange}
                            placeholder="Поиск"
                            value={query}
                        />
                    </div>
                    <div className="col-lg-3">
                        <FormSelect
                            onChange={this.handleAreaChange}
                            value={area}
                            name="area"
                            placeholder="Направление"
                            isClearable={true}
                            options={areas}
                            key="area"
                        />
                    </div>
                    <div className="col-lg-3">
                        <FormSelect
                            onChange={this.handleYearChange}
                            value={year}
                            name="year"
                            isClearable={true}
                            placeholder="Год выпуска"
                            options={years}
                            key="year"
                        />
                    </div>
                    <div className="col-lg-3">
                        <FormSelect
                            onChange={this.handleCityChange}
                            value={city}
                            name="city"
                            isClearable={true}
                            placeholder="Город"
                            options={cities}
                            key="city"
                        />
                    </div>
                </div>
                <UserCardList users={filteredItems} />
            </div>
        );
    }
}

export default Alumni;