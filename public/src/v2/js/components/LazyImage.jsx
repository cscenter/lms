import React from 'react';
import {useInView} from 'react-intersection-observer';
import * as PropTypes from 'prop-types';

const LazyImage = ({width, height, src, className = '', rootMargin = '150px', ...rest}) => {
    const [ref, inView] = useInView({
        threshold: 0,
        triggerOnce: true,
        rootMargin: rootMargin
    });

    return (
        <div ref={ref} className={className}>
            {inView ? (
                <img alt="" {...rest} src={src}/>
            ) : null}
        </div>
    );
};

LazyImage.propTypes = {
    width: PropTypes.number,
    height: PropTypes.number,
    src: PropTypes.string.isRequired,
    className: PropTypes.string,
    rootMargin: PropTypes.string,
};

export default LazyImage;