import * as PropTypes from 'prop-types';

export const optionIntType = PropTypes.shape({
    value: PropTypes.number.isRequired,
    label: PropTypes.string.isRequired
});

export const optionStrType = PropTypes.shape({
    value: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired
});

export const refType = PropTypes.oneOfType([PropTypes.func, PropTypes.object]);