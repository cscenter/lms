const path = require('path');
const webpack = require('webpack');

// const APP_VERSION = process.env.APP_VERSION || "v1";

module.exports = {
    devtool: "cheap-eval-source-map",

    output: {
        publicPath: 'http://localhost:8081/static/',
    },

    plugins: [
        new webpack.DefinePlugin({
            'process.env': {
                NODE_ENV: '"development"'
            },
            '__DEVELOPMENT__': true
        }),
        new webpack.NamedModulesPlugin(),
        new webpack.HotModuleReplacementPlugin()
    ],

    devServer: {
        // FIXME: похоже, можно удалить, т.к. не используется (убедиться в этом)
        // contentBase: path.resolve(__dirname, `../cscsite/assets/${APP_VERSION}/dist/js`),
        port: 8081,
        hot: true,
        headers: { "Access-Control-Allow-Origin": "*" }
    },
};
