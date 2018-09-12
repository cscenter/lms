import React from 'react';
import PropTypes from 'prop-types';

class UserCard extends React.Component {
    static defaultProps = {
        className: 'user-card'
    };

    render() {
        let {id, photo, name, sex, workplace} = this.props;
        return (
            <a className={this.props.className}
               href={`/users/${id}/`}
               id={`user-card-${id}`}>
                <div className={`user-card__photo _${sex}`}>
                    {photo !== null ? <img src={photo} alt={name} /> : ""}
                </div>
                <div className="user-card__details">
                    {name}
                    {workplace !== null ? <div className="workplace">{workplace}</div> : ""}
                </div>
            </a>
        );
    }
}

UserCard.propTypes = {
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired
};

export default UserCard;
