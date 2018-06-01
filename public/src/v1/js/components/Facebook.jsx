import React, {Fragment} from 'react';
import Select from 'react-select';
import PropTypes from 'prop-types';
import _debounce from 'lodash-es/debounce';
import _isEqual from 'lodash-es/isEqual';

import UserCardList from 'components/UserCardList';
import SearchInput from 'components/SearchInput';


class FormSelect extends React.Component {

    handleChange = (e) => {
        this.props.onChange(e);
    };

    render() {
        return (
            <Select
                name={this.props.name}
                value={this.props.value}
                {...this.props}
                onChange={this.handleChange}
                clearable={false}
                searchable={false}
            />
        );
    }
}

FormSelect.propTypes = {
    onChange: PropTypes.func.isRequired,
    options: PropTypes.array.isRequired
};

// TODO: replace with HOC `UserCardFilter`
class Facebook extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            "items": [],
        };
        this.fetch = _debounce(this.fetch, 300);
    }

    handleSearchInputChange = (value) => {
        this.setState({
            query: value,
        });
    };

    handleYearChange = (year) => {
        this.setState({
            enrollment_year: year
        });
    };

    handleCityChange = (city) => {
        this.setState({
            city: city
        });
    };

    componentDidMount = () => {
        // Set initial state and fetch data
        this.setState(this.props.init.state);
    };

    componentWillUnmount = function () {
        this.serverRequest.abort();
    };

    componentDidUpdate = (prevProps, prevState) => {
        this.fetch(prevState);
    };

    fetch = (prevState) => {
        const newFilterState = this.getFilterState(this.state);
        const newPayload = this.getRequestPayload(newFilterState);
        if (prevState !== null) {
            const prevFilterState = this.getFilterState(prevState);
            const prevPayload = this.getRequestPayload(prevFilterState);
            if (!_isEqual(prevPayload, newPayload)) {
                this._fetch(newPayload);
            }
        } else {
            this._fetch(newPayload);
        }
    };

    getFilterState(state) {
        let {enrollment_year, city, query} = state;
        return {enrollment_year, city, query};
    }

    getRequestPayload(filterState) {
        let {query, ...payload} = filterState;
        return payload;
    }

    _fetch = (payload) => {
        this.serverRequest = $.ajax({
            type: "POST",
            url: this.props.init.entry_url,
            data: payload,
            dataType: "json"
        }).done((result) => {
            this.setState({
                items: result.items,
            });
        });

    };

    render() {
        const {enrollment_year, city, query} = this.state;
        const {optionsEnrollmentYear, optionsCity} = this.props.init.options;

        let filteredItems = this.state.items.filter(function(item) {
          return item.full_name.toLowerCase().search(
            query.toLowerCase()) !== -1;
        });

        return (
            <div className="container">
                <h1>Студенты</h1>
                <div className="row">
                    <div className="col-xs-4">
                        <SearchInput
                            onChange={this.handleSearchInputChange}
                            placeholder="Поиск"
                            value={query}
                        />
                    </div>
                    <div className="col-xs-4">
                        <FormSelect
                            onChange={this.handleYearChange}
                            value={enrollment_year}
                            name="enrollment_year"
                            placeholder="Год поступления"
                            options={optionsEnrollmentYear}
                            key="enrollment_year"
                        />
                    </div>
                    <div className="col-xs-4">
                        <FormSelect
                            onChange={this.handleCityChange}
                            value={city}
                            name="city"
                            placeholder="Город"
                            options={optionsCity}
                            key="city"
                        />
                    </div>
                </div>
                <div className="row">
                    <UserCardList className="graduates-list" users={filteredItems} />
                </div>
            </div>
        );
    }
}

export default Facebook;