
const webpack = require('webpack');
// const ChunkManifestPlugin = require("chunk-manifest-webpack-plugin");
const WebpackChunkHash = require('webpack-chunk-hash');
const UglifyJSPlugin = require('uglifyjs-webpack-plugin');


module.exports = {
    output: {
        filename: '[name]-[chunkhash].js',
        chunkFilename: '[name]-[chunkhash].js',
        publicPath: '/static/v1/dist/js/',
    },

    plugins: [
        new webpack.DefinePlugin({
            'process.env': {
                NODE_ENV: '"production"'
            },
            '__DEVELOPMENT__': false
        }),
        new UglifyJSPlugin({
            parallel: true,
            uglifyOptions: {
                compress: {
                    warnings: false
                }
            }
        }),
        // Need this plugin for deterministic hashing
        // until this issue is resolved: https://github.com/webpack/webpack/issues/1315
        new webpack.HashedModuleIdsPlugin(),
        new WebpackChunkHash(),
        // TODO: Lets wait until inlining manifest JSON support in django-webpack-loader
        // new ChunkManifestPlugin({
        //     filename: "chunk-manifest.json",
        //     manifestVariable: "webpackManifest"
        // })
    ],
};
