/**
 * It's impossible to extend babel configuration for vendor js modules placed
 * in `node_modules/`. @babel/core stop looking for `.babelrc` if it found
 * `node_modules` during the module path traversing (since this directory
 * is a root for _vendor_ packages).
 * Some packages (e.g. `bootstrap`) could use ES6 syntax without providing
 * .babelrc what leads to import errors. To fix these broken modules we can:
 * * Create global configuration `babel.config.js` (could affect on gulp/v1 configuration)
 * * Mock them
 * * Customize babel-jest and directly pass in global options
**/

const babelOptions = {
    plugins: [
        "@babel/plugin-proposal-object-rest-spread",
        "@babel/plugin-transform-modules-commonjs",
    ]
};

module.exports = require('babel-jest').createTransformer(babelOptions);