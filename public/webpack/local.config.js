const path = require('path');

const APP_VERSION = process.env.APP_VERSION || "v1";

let __outputdir = path.join(__dirname, `../assets/${APP_VERSION}/dist/.local`);

module.exports = {
    devtool: "cheap-eval-source-map",

    output: {
        path: __outputdir,
        publicPath: `/static/${APP_VERSION}/dist/.local/`,
    },
};
