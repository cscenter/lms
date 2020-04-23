const path = require('path');
const BundleTracker = require('webpack-bundle-tracker');

const APP_VERSION = process.env.APP_VERSION || "v1";

let __outputdir = path.join(__dirname, `../assets/${APP_VERSION}/dist/.local`);
let __bundlesdir = path.join(__dirname, `../assets/${APP_VERSION}/dist`);

module.exports = {
    devtool: "source-map",

    output: {
        path: __outputdir,
        publicPath: `/static/${APP_VERSION}/dist/.local/`,
    },

    plugins: [
        new BundleTracker({
            path: path.join(__bundlesdir, '.local'),
            filename: `webpack-stats-${APP_VERSION}.json`
        }),
    ]
};
