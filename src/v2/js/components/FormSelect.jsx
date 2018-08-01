import Select from 'react-select';
import PropTypes from 'prop-types';
import React from 'react';

class FormSelect extends React.Component {

    handleChange = (e) => {
        this.props.onChange(e);
    };

    render() {
        return (
            <Select
                name={this.props.name}
                value={this.props.value}
                clearable={false}
                className='react-select-container'
                classNamePrefix='react-select'
                getStyles={() => {}}
                {...this.props}
                onChange={this.handleChange}
                isSearchable={false}
            />
        );
    }
}

FormSelect.propTypes = {
    onChange: PropTypes.func.isRequired,
    options: PropTypes.array.isRequired
};

export default FormSelect;