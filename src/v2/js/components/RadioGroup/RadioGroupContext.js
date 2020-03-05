import React from 'react';

const RadioGroupContext = React.createContext();

if (process.env.NODE_ENV === 'development') {
    RadioGroupContext.displayName = 'RadioGroupContext';
}

export default RadioGroupContext;
