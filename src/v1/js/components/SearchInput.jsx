import React from 'react';
import PropTypes from 'prop-types';

class SearchInput extends React.Component {
    static defaultProps = {
        value: ''
    };

    handleChange = (e) => {
        this.props.onChange(e.target.value);
    };

    render() {
        return (
            <input
                name="query"
                type="text"
                className="form-control"
                autoComplete="off"
                {...this.props}
                onChange={this.handleChange}
            />
        );
    }
}

SearchInput.propTypes = {
    onChange: PropTypes.func.isRequired,
    value: PropTypes.string.isRequired
};

export default SearchInput;