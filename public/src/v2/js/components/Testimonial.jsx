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
            <div className="ui author _testimonial">
                <img className="author__img" alt={author} src={photo} width={imgWidth} height={imgHeight} />
                <div className="author__details">
                        <h4>{ author }</h4>
                        <span>Выпуск {year}, {areas}</span>
                </div>
                <div className="author__testimonial" dangerouslySetInnerHTML={{__html: text}} />
            </div>
        );
    }
}

Testimonial.propTypes = {
    id: PropTypes.number.isRequired,
    author: PropTypes.string.isRequired
};

export default Testimonial;
