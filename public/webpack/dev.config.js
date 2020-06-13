const path = require('path');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');

const APP_VERSION = process.env.APP_VERSION || "v1";

let __outputdir = path.join(__dirname, `../assets/${APP_VERSION}/dist/local`);

module.exports = {
    mode: "development",
    devtool: "cheap-eval-source-map",

    output: {
        publicPath: 'http://csc.test:8081/',
    },

    plugins: [
        new webpack.DefinePlugin({
            'process.env': {
                NODE_ENV: '"development"'
            },
        }),
        new webpack.HotModuleReplacementPlugin(),
        new BundleTracker({
            path: __outputdir,
            filename: `webpack-stats-${APP_VERSION}-dev.json`
        }),
    ],

    // This is default settings for development mode, but lets set it explicitly
    optimization: {
        namedModules: true,
        concatenateModules: false,
        runtimeChunk: 'single',
    },

    devServer: {
        port: 8081,
        hot: true,
        host: '0.0.0.0',
        headers: { "Access-Control-Allow-Origin": "*" },
        allowedHosts: [
            '.csc.test',
        ]
    },
};
