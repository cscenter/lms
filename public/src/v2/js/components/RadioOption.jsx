import React from 'react';
import * as PropTypes from 'prop-types';
import useRadioGroup from 'components/RadioGroup/useRadioGroup';


const RadioOption = React.forwardRef(function RadioOption(props, ref) {
    const {id, value, children, disabled = false} = props;

    const {selected, onChange, name, required, groupDisabled} = useRadioGroup();
    const radioProps = {
        disabled: (disabled || groupDisabled),
        id,
        value: value || id,
        name,
        onChange,
    };
    if (selected) radioProps.checked = selected === id;
    return (
        <label className={`ui option radio`}>
            <input
                required={required}
                className="control__input"
                type="radio"
                ref={ref}
                {...radioProps}
            />
            <span className="control__indicator"/>
            <span className="control__description">{children}</span>
        </label>
    );
});


RadioOption.propTypes = {
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    className: PropTypes.string,
    children: PropTypes.node.isRequired,
    disabled: PropTypes.bool,
    onChange: PropTypes.func,
};


export default RadioOption;
