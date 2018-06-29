import React from 'react';
import PropTypes from 'prop-types';

// TODO: из-за стилей на тег img (height: auto) браузер не знает, какие размеры выделить под рендеринг картинги до полной загрузки источника. Надо ему как-то помочь с этим
class UserCard extends React.Component {
    static defaultProps = {
        imgInitialWidth: 170,
        imgInitialHeight: 238,
        className: 'user-card'
    };

    render() {
        let imgSrc = this.props.photo;
        if (imgSrc === null) {
            let gender = (this.props.sex  === "m" ? "boy" : "girl");
            imgSrc = `/static/v2/img/placeholder/${gender}.png`;
        }
        return (
            <a className={this.props.className}
               href={`/users/${this.props.id}/`}
               id={`user-card-${this.props.id}`}>
                <div className="user-card__photo">
                    <img height={this.props.imgInitialHeight} width={this.props.imgInitialWidth} src={imgSrc} alt={this.props.name} />
                </div>
                <div className="user-card__details">{this.props.name}</div>
            </a>
        );
    }
}

UserCard.propTypes = {
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired
};

export default UserCard;
