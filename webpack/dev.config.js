const path = require('path');
const webpack = require('webpack');

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
    ],

      devServer: {
        contentBase: path.resolve(__dirname, '../cscsite/assets/js/dist'),
          port: 8081,
      },
};
