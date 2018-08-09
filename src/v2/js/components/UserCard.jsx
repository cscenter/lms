import React from 'react';
import PropTypes from 'prop-types';

class UserCard extends React.Component {
    static defaultProps = {
        className: 'user-card'
    };

    render() {
        let imgSrc = this.props.photo;
        let gender = (this.props.sex  === "m" ? "boy" : "girl");
        let placeholder = `/static/v2/img/placeholder/${gender}.png`;
        return (
            <a className={this.props.className}
               href={`/users/${this.props.id}/`}
               id={`user-card-${this.props.id}`}>
                <div className={`user-card__photo _${this.props.sex}`} style={{"background":placeholder}}>
                    {imgSrc !== null ? <img src={imgSrc} alt={this.props.name} /> : ""}
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
