import React from 'react';
import PropTypes from 'prop-types';
import LazyImage from "./LazyImage";

class UserCard extends React.Component {
    static defaultProps = {
        className: 'user-card'
    };

    render() {
        let {id, photo, name, url, workplace} = this.props;
        return (
            <a className={this.props.className}
               href={url}
               id={`user-card-${id}`}>
                <LazyImage src={photo} alt={name} className={`user-card__photo`} />
                <div className="user-card__details">
                    {name}
                    {workplace !== null ? <div className="workplace">{workplace}</div> : ""}
                </div>
            </a>
        );
    }
}

const propTypes = {
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    url: PropTypes.string.isRequired,
    photo: PropTypes.string.isRequired,
    workplace: PropTypes.string,
};

UserCard.propTypes = propTypes;

export default UserCard;
