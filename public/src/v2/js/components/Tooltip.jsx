import React from 'react';
import * as PropTypes from 'prop-types';
import {Tooltip as BaseTooltip} from 'react-tippy';

export const Tooltip = ({ title, children, ...options }) => (
    <BaseTooltip animation={`fade`}
                 arrow={true}
                 arrowSize={`small`}
                 size={`regular`}
                 theme={`dark`}
                 {...options}
                 title={title}>
      {children}
    </BaseTooltip>
);

Tooltip.propTypes = {
    title: PropTypes.string.isRequired,
    children: PropTypes.element.isRequired
};
