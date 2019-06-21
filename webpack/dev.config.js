const path = require('path');
const webpack = require('webpack');

module.exports = {
    mode: "development",
    devtool: "cheap-eval-source-map",

    output: {
        publicPath: 'http://csc.test:8081/static/',
    },

    plugins: [
        new webpack.DefinePlugin({
            'process.env': {
                NODE_ENV: '"development"'
            },
            '__DEVELOPMENT__': true
        }),
        new webpack.HotModuleReplacementPlugin()
    ],

    // This is default settings for development mode, but lets set it explicitly
    optimization: {
        namedModules: true,
        concatenateModules: false
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
