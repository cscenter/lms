import SelectBase from 'react-select';
import CreatableSelectBase from 'react-select/creatable';
import * as PropTypes from 'prop-types';
import React from 'react';


const selectOptionType = PropTypes.shape({
    value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    label: PropTypes.string.isRequired
});


const selectDefaultProps = {
    clearable: false,
    className: 'react-select-container',
    classNamePrefix: 'react-select',
    formatCreateLabel: (inputValue) => { // eslint-disable-line react/display-name
        return <React.Fragment><b>Добавить</b> &quot;{inputValue}&quot;
        </React.Fragment>;
    }
};

const selectDefaultStyles = {
    input: (provided, state) => ({
        ...provided,
        paddingBottom: 0,
        paddingTop: 0,
        marginTop: 0,
        marginBottom: 0,
    }),
};

export function getOptionByValue(options, value) {
    let option = options.find((option) => option.value === value);
    return option !== undefined ? option : null;
}


export function Select({name, onChange, errors = {}, ...props}) {
    function handleChange(e) {
        onChange(e, name);
    }

    const hasError = Object.prototype.hasOwnProperty.call(errors, name);
    return (
        <SelectBase
            name={name}
            {...selectDefaultProps}
            styles={selectDefaultStyles}
            className={hasError ? `${selectDefaultProps.className} error`: selectDefaultProps.className}
            {...props}
            onChange={handleChange}
            isSearchable={false}
        />
    );
}

Select.propTypes = {
    name: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
    options: PropTypes.array.isRequired,
    errors: PropTypes.object,
};

export function CreatableSelect({name, onChange, styles = {}, errors = {}, ...props}) {
    function handleChange(e) {
        onChange(e, name);
    }

    const selectStyles = Object.assign({}, selectDefaultStyles, styles);
    const hasError = Object.prototype.hasOwnProperty.call(errors, name);
    return (
        <CreatableSelectBase
            {...selectDefaultProps}
            styles={selectStyles}
            className={hasError ? `${selectDefaultProps.className} error`: selectDefaultProps.className}
            {...props}
            onChange={handleChange}
        />
    );
}

CreatableSelect.propTypes = {
    name: PropTypes.string.isRequired,
    value: selectOptionType,
    onChange: PropTypes.func.isRequired,
    styles: PropTypes.object,
    errors: PropTypes.object,
};
