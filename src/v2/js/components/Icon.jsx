import React from 'react';
import cx from 'classnames';
import PropTypes from 'prop-types';

const Icon = ({ id, className = '' }) => (
    <svg aria-hidden="true"
         className={cx(`sprite-img svg-icon _${id}`, className)}
         xmlnsXlink="http://www.w3.org/1999/xlink">
        <use xlinkHref={`#${id}`}/>
    </svg>
);

Icon.propTypes = {
    id: PropTypes.string.isRequired,
    className: PropTypes.string,
};

export default Icon;
