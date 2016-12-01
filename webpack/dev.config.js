const webpack = require('webpack');

module.exports = {
    devtool: 'source-map', // 'cheap-module-eval-source-map',

    entry: {
        vendor: [
        ]
    },

    module: {
        loaders: [],
    },

    plugins: [
        new webpack.DefinePlugin({
            'process.env': {
                NODE_ENV: '"development"'
            },
            '__DEVELOPMENT__': true
        }),
        new webpack.optimize.OccurrenceOrderPlugin()
    ],
};
