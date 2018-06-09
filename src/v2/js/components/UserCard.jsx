import React from 'react';
import PropTypes from 'prop-types';
import LazyLoad from 'react-lazyload';


class UserCard extends React.Component {
    static defaultProps = {
        imgHeight: 238,
        imgWidth: 170,
        className: 'user-card'
    };

    render() {
        return (
            <div className={this.props.className}>
                <LazyLoad height={this.props.imgHeight} once offset={100}>
                    <img src={this.props.photo} width={this.props.imgWidth} height={this.props.imgHeight} />
                </LazyLoad>
                <a href={`/users/${this.props.id}/`}>{this.props.name}</a>
            </div>
        );
    }
}

UserCard.propTypes = {
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired
};

export default UserCard;
