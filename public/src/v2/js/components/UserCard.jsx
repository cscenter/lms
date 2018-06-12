import React from 'react';
import PropTypes from 'prop-types';
import LazyLoad from 'react-lazyload';


class UserCard extends React.Component {
    static defaultProps = {
        imgInitialWidth: 170,
        imgInitialHeight: 238,
        className: 'user-card'
    };

    render() {
        return (
            <a className={this.props.className}
               href={`/users/${this.props.id}/`}
               id={`user-card-${this.props.id}`}>
                <div className="user-card__photo">
                    <LazyLoad height={this.props.imgInitialHeight}
                              throttle={200}
                          once
                          offset={200}>
                        <img src={this.props.photo} alt={this.props.name} />
                    </LazyLoad>
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
