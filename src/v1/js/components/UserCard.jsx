import React from 'react';
import PropTypes from 'prop-types';


class UserCard extends React.Component {
    static defaultProps = {
        className: 'alumni'
    };

    render() {
        return (
            <div className={this.props.className}>
                <img src={this.props.photo} width="170" height="238" />
                <a href={this.props.profile_url}>{this.props.full_name}</a>
            </div>
        );
    }
}

UserCard.propTypes = {
    id: PropTypes.number.isRequired,
    photo: PropTypes.string.isRequired,
    profile_url: PropTypes.string.isRequired,
    full_name: PropTypes.string.isRequired
};

export default UserCard;
