import * as PropTypes from 'prop-types';

export const selectOptionType = PropTypes.shape({
    value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    label: PropTypes.string.isRequired
});