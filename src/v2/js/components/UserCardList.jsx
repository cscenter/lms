import React from 'react';
import * as PropTypes from 'prop-types';

import UserCard from './UserCard';

class UserCardList extends React.Component {
    static defaultProps = {
        className: 'card-deck _users'
    };

    render() {
        return (
            <div className={this.props.className}>
                {this.props.users.map((user) => {
                    return <UserCard key={`user-${user.id}`} {...user} />;
                })}
            </div>
        );
    }
}

UserCardList.propTypes = {
    className: PropTypes.string,
    users: PropTypes.arrayOf(PropTypes.object)
};

export default UserCardList;
