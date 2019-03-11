import React from 'react';
import PropTypes from 'prop-types';
import cx from 'classnames';
import {Consumer} from './RadioGroupContext';


const RadioOption = ({
                         id,
                         value,
                         children,
                         disabled: optionDisabled,
                         className: optionClassName,
                     }) => (
    <Consumer>
        {({
              selected,
              onChange,
              name,
              disabled: groupDisabled,
              className: groupClassName,
              required: optionRequired
          }) => {
            const className = cx(optionClassName, groupClassName);
            const disabled = optionDisabled || groupDisabled;

            const radioProps = {
                disabled,
                id,
                value: value || id,
                name,
                onChange,
            };
            if (selected) radioProps.checked = (selected === id);

            return (
                <label className={`ui option radio`}>
                    <input
                        required={optionRequired}
                        className="control__input"
                        type="radio"
                        {...radioProps}
                    />
                    <span className="control__indicator"/>
                    <span className="control__description">{children}</span>
                </label>
            );
        }}
    </Consumer>
);


RadioOption.defaultProps = {
    className: '',
    disabled: false,
    onChange: () => false,
    selected: undefined,
    required: false,
};


RadioOption.propTypes = {
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    /** Additional classes. */
    className: PropTypes.string,
    children: PropTypes.node,
    disabled: PropTypes.bool,
    onChange: PropTypes.func,
};


export default RadioOption;
