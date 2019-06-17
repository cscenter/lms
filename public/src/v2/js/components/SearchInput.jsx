import React from 'react';
import PropTypes from 'prop-types';
import Icon from "./Icon";

import _debounce from 'lodash-es/debounce';

function InputIcon(props) {
    const icon = props.icon;
    if (icon !== null) {
        return (
            <i className={`_${icon} icon`}>
                <Icon id={icon}/>
            </i>
        );
    }

    return null;
}

class SearchInput extends React.Component {
    static defaultProps = {
        query: ''
    };

    constructor(props) {
        super(props);
        this.state = {
            query: this.props.query
        };
        // TODO: https://stackoverflow.com/a/28046731/1341309
        this.handleChangeDebounced = _debounce(this.props.handleSearch, 200);
    }

    handleChange = (e) => {
        this.setState({query: e.target.value}, () => {
            this.handleChangeDebounced(this.state.query);
        });
    };

    render() {
        const {icon} = this.props;
        const iconClass = icon !== null ? "icon" : "";
        return (
            <div className={`ui ${iconClass} input`}>
                <input
                    name="query"
                    type="text"
                    autoComplete="off"
                    value={this.state.query}
                    onChange={this.handleChange}
                />
                <InputIcon icon={icon}/>
            </div>
        );
    }
}

SearchInput.propTypes = {
    handleSearch: PropTypes.func.isRequired,
    query: PropTypes.string.isRequired
};

export default SearchInput;