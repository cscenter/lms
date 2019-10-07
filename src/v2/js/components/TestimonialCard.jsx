import React from 'react';
import PropTypes from 'prop-types';


class TestimonialCard extends React.Component {
    static defaultProps = {
        imgWidth: 74,
        imgHeight: 74,
        className: 'user-card'
    };

    render() {
        const {student, photo, imgWidth, imgHeight, testimonial, year, areas} = this.props;
        return (
            <div className="ui author _testimonial">
                <img className="author__img" alt={student} src={photo} width={imgWidth} height={imgHeight} />
                <div className="author__details">
                        <h4>{ student }</h4>
                        <span>Выпуск {year}, {areas}</span>
                </div>
                <div className="author__testimonial" dangerouslySetInnerHTML={{__html: testimonial}} />
            </div>
        );
    }
}

TestimonialCard.propTypes = {
    id: PropTypes.number.isRequired,
    student: PropTypes.string.isRequired
};

export default TestimonialCard;
