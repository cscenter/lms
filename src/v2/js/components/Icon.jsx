import React from 'react';

class Icon extends React.Component {

    render() {
        return (
            <svg aria-hidden="true"
                 className={`sprite-img _${ this.props.id }`}
                 xmlnsXlink="http://www.w3.org/1999/xlink">
                <use xlinkHref={`#${ this.props.id}`}/>
            </svg>
        );
    }
}

export default Icon;
