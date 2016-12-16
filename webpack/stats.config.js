const webpack = require('webpack');
const path = require('path');

module.exports = {
    // entry: ['babel-polyfill', "./cscsite/assets/src/js/stats/main"],
    entry: "./cscsite/assets/src/js/stats/main",
    resolve: {
        modulesDirectories: [
            "."
        ],
        // FIXME: no idea how to load it with webpack correctly
        alias: {
            moment: path.join(__dirname, "/../cscsite/assets/js/vendor/moment/moment.min.js")
        },
    },
    plugins: [
        new webpack.ProvidePlugin({
            'd3': 'd3',
            '$': 'jquery',
            'jQuery': 'jquery',
            'window.jQuery': 'jquery',
            'c3': 'c3'
        }),
        // new webpack.IgnorePlugin(/^\.\/locale$/, [/moment$/])
    ],
    output: {
        path: __dirname + "/../cscsite/assets/js/",
        filename: "stats.bundle.js",
        publicPath: "/static/"
    },
    externals: {
        // require("jquery") is external and available on the global var jQuery
        "jquery": "jQuery",
        "d3": "d3",
        "c3": "c3",

    },
    module: {
        loaders: [
            {
                test: /\.js$/,
                loaders: ['babel-loader'],
                exclude: /node_modules/,
            }
        ]
    }
};