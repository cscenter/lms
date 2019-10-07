import React from 'react';
import * as PropTypes from 'prop-types';
import cx from 'classnames';
import {Provider} from './RadioGroupContext';

Provider.displayName = 'RadioGroupProvider';


const RadioGroup = ({
                        selected,
                        onChange,
                        name,
                        disabled,
                        required,
                        children,
                        className,
                    }) => (
    <Provider
        value={{
            selected,
            onChange,
            name,
            disabled,
            required,
            className,
        }}
    >
        <div className={cx("grouped", className)}>
            {children}
        </div>
    </Provider>
);

RadioGroup.propTypes = {
    children: PropTypes.node.isRequired,
    name: PropTypes.string.isRequired,
    selected: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    onChange: PropTypes.func,
    disabled: PropTypes.bool,
    /** Additional classes. */
    className: PropTypes.string,
};


RadioGroup.defaultProps = {
    className: '',
    disabled: false,
    onChange: () => false,
    selected: undefined,
};

export default RadioGroup;
