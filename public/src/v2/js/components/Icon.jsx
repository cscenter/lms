import React from 'react';
import cx from 'classnames';

const Icon = ({ id, className = '' }) => (
    <svg aria-hidden="true"
         className={cx(`sprite-img svg-icon _${id}`, className)}
         xmlnsXlink="http://www.w3.org/1999/xlink">
        <use xlinkHref={`#${id}`}/>
    </svg>
);

export default Icon;
