const path = require('path');
const webpack = require('webpack');

const TerserPlugin = require('terser-webpack-plugin');
const SentryWebpackPlugin = require('@sentry/webpack-plugin');
const DeleteSourceMapWebpackPlugin = require('delete-sourcemap-webpack-plugin');

const APP_VERSION = process.env.APP_VERSION || "v1";

let __bundlesdir = path.join(__dirname, `../assets/${APP_VERSION}/dist/js`);

// TODO: add css minimization
module.exports = {
    mode: "production",

    devtool: "hidden-source-map",

    output: {
        filename: '[name]-[chunkhash].js',
        sourceMapFilename: '[name]-[chunkhash].js.map',
        chunkFilename: '[name]-[chunkhash].js',
        publicPath: `/static/${APP_VERSION}/dist/js/`,
    },

    stats: {
        colors: false,
        hash: true,
        timings: true,
        assets: true,
        chunks: true,
        chunkModules: true,
        modules: true,
        children: true,
    },

    optimization: {
        namedModules: false,
        concatenateModules: true,
        minimizer: [
            new TerserPlugin({
                sourceMap: true, // Must be set to true if using source-maps in production
                terserOptions: {
                    compress: {
                        pure_funcs: [ "console.debug" ]
                    },
                },
            }),
        ],
    },

    plugins: [
        new webpack.DefinePlugin({
            'process.env.NODE_ENV': '"production"',
            '__DEVELOPMENT__': false
        }),
        // Need this plugin for deterministic hashing
        // until this issue is resolved: https://github.com/webpack/webpack/issues/1315
        new webpack.HashedModuleIdsPlugin(),
        new SentryWebpackPlugin({
            include: [
                __bundlesdir
            ],
            ignoreFile: '.sentrycliignore',
            ignore: ['node_modules'],
            urlPrefix: `/static/${APP_VERSION}/dist/js`,
            debug: true,
            dryRun: false,
            // Fail silently in case no auth data provided to the sentry-cli
            errorHandler: function(err, invokeErr) {
                console.log(`Sentry CLI Plugin: ${err.message}`);
            },
        }),
        // Delete source maps after uploading to sentry.io
       new DeleteSourceMapWebpackPlugin()
    ],
};
