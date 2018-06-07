import React from 'react';

import UserCard from './UserCard';

class UserCardList extends React.Component {
    static defaultProps = {
        className: ''
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

export default UserCardList;
