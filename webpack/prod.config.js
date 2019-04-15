const webpack = require('webpack');

const TerserPlugin = require('terser-webpack-plugin');

const APP_VERSION = process.env.APP_VERSION || "v1";

// TODO: add css minimization
module.exports = {
    mode: "production",
    output: {
        filename: '[name]-[chunkhash].js',
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
                sourceMap: false, // Must be set to true if using source-maps in production
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
    ],
};
