import React from 'react';
import PropTypes from 'prop-types';


class Testimonial extends React.Component {
    static defaultProps = {
        imgWidth: 74,
        imgHeight: 74,
        className: 'user-card'
    };

    render() {
        const {author, photo, imgWidth, imgHeight, text, year, areas} = this.props;
        return (
            <div className="testimonial">
                <img className="img-rounded" alt={author} src={photo} width={imgWidth} height={imgHeight} />
                <div className="testimonial__details">
                    <div className="testimonial__author">
                        <h4>{ author }</h4>
                        <span>Выпуск {year}, {areas}</span>
                    </div>
                    <div className="testimonial__text" dangerouslySetInnerHTML={{__html: text}} />
                </div>
            </div>
        );
    }
}

Testimonial.propTypes = {
    id: PropTypes.number.isRequired,
    author: PropTypes.string.isRequired
};

export default Testimonial;
