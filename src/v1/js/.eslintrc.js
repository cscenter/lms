const path = require('path');

module.exports = {
    "root": true,
    "rules": {
        "react/jsx-filename-extension": 0
    },
    "parser": "babel-eslint",
    "parserOptions": {
        "ecmaVersion": 6,
        "sourceType": "module",
        "ecmaFeatures": {
            "experimentalObjectRestSpread": true,
            "modules": true
        }
    },
    "env": {
        "es6": true,
        // "browser": true,
        // "jest": true
    },
    "settings": {
        "import/resolver": {
            "webpack": {
                // Relative paths will be resolved relative to the source's nearest package.json or
                // the process's current working directory if no package.json is found
                "config": path.resolve('./webpack/v1.config.js')
            }
        }
    }
};
