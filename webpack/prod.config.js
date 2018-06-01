const webpack = require('webpack');

const APP_VERSION = process.env.APP_VERSION || "v1";

// TODO: add css minimization
module.exports = {
    mode: "production",
    output: {
        filename: '[name]-[chunkhash].js',
        chunkFilename: '[name]-[chunkhash].js',
        publicPath: `/static/${APP_VERSION}/dist/js/`,
    },

    optimization: {
        namedModules: false,
        concatenateModules: true
    },

    plugins: [
        new webpack.DefinePlugin({
            'process.env': {
                NODE_ENV: '"production"'
            },
            '__DEVELOPMENT__': false
        }),
        // Need this plugin for deterministic hashing
        // until this issue is resolved: https://github.com/webpack/webpack/issues/1315
        new webpack.HashedModuleIdsPlugin(),
    ],
};
