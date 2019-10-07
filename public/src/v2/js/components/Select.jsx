import SelectBase from 'react-select';
import * as PropTypes from 'prop-types';
import React from 'react';


export const SelectDefaultProps = {
    clearable: false,
    className: 'react-select-container',
    classNamePrefix: 'react-select',
    styles: {
        input: (provided, state) => ({
            ...provided,
            paddingBottom: 0,
            paddingTop: 0,
            marginTop: 0,
            marginBottom: 0,
        }),
    },
    formatCreateLabel: (inputValue) => {
        return <React.Fragment><b>Добавить</b> "{inputValue}"</React.Fragment>;
    }
};

export function getOptionByValue(options, value) {
    let option = options.find((option) => option.value === value);
    return option !== undefined ? option : null;
}


export class Select extends React.Component {

    handleChange = (e) => {
        this.props.onChange(e, this.props.name);
    };

    render() {
        return (
            <SelectBase
                name={this.props.name}
                value={this.props.value}
                {...SelectDefaultProps}
                {...this.props}
                onChange={this.handleChange}
                isSearchable={false}
            />
        );
    }
}

Select.propTypes = {
    onChange: PropTypes.func.isRequired,
    options: PropTypes.array.isRequired
};
