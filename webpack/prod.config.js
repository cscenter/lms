const webpack = require('webpack');

module.exports = {
    output: {
        filename: '[name]-[chunkhash].js',
    },

    plugins: [
        new webpack.DefinePlugin({
            'process.env': {
                NODE_ENV: '"production"'
            },
            '__DEVELOPMENT__': false
        }),
        new webpack.optimize.DedupePlugin(),
        new webpack.optimize.OccurrenceOrderPlugin(),
        new webpack.optimize.UglifyJsPlugin({
            compress: {
                warnings: false
            }
        }),
    ],
};
