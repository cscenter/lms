import React from 'react';
import * as PropTypes from 'prop-types';
import LazyImage from "./LazyImage";

class UserCard extends React.Component {
    static defaultProps = {
        className: 'card _user'
    };

    render() {
        let {id, photo, name, url, activities: subtitle} = this.props;
        return (
            <a className={this.props.className}
               href={url}
               id={`user-card-${id}`}>
                <LazyImage src={photo} alt={name} className={`card__img`} />
                <div className="card__title">{name}</div>
                {subtitle ? <div className="card__subtitle">{subtitle}</div> : ""}
            </a>
        );
    }
}

const propTypes = {
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    url: PropTypes.string.isRequired,
    photo: PropTypes.string.isRequired,
    activities: PropTypes.string,
};

UserCard.propTypes = propTypes;

export default UserCard;
