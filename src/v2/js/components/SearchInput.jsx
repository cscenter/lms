import React from 'react';
import * as PropTypes from 'prop-types';
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
        debounceMaxWait: 200,
        placeholder: '',
        query: ''
    };

    constructor(props) {
        super(props);
        this.state = {
            query: this.props.query
        };
        // TODO: https://stackoverflow.com/a/28046731/1341309
        this.handleChangeDebounced = _debounce(this.props.handleSearch,
                                               this.props.debounceMaxWait);
    }

    componentWillUnmount() {
        this.handleChangeDebounced.cancel();
    }

    handleChange = (e) => {
        this.setState({query: e.target.value}, () => {
            this.handleChangeDebounced(this.state.query, this.props.name);
        });
    };

    render() {
        const {icon, placeholder, name} = this.props;
        const iconClass = icon !== null ? "icon" : "";
        return (
            <div className={`ui ${iconClass} input`}>
                <input
                    type="text"
                    autoComplete="off"
                    name={name}
                    value={this.state.query}
                    onChange={this.handleChange}
                    placeholder={placeholder}
                />
                <InputIcon icon={icon}/>
            </div>
        );
    }
}

SearchInput.propTypes = {
    debounceMaxWait: PropTypes.number.isRequired,
    handleSearch: PropTypes.func.isRequired,
    name: PropTypes.string.isRequired,
    query: PropTypes.string.isRequired,
};

export default SearchInput;