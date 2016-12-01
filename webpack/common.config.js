const path = require('path');
const autoprefixer = require('autoprefixer');
// const postcssImport = require('postcss-import');
const merge = require('webpack-merge');
// const HtmlWebpackPlugin = require('html-webpack-plugin');
const webpack = require('webpack');
const CleanWebpackPlugin = require('clean-webpack-plugin');


const development = require('./dev.config');
const production = require('./prod.config');

require('babel-polyfill').default;

const TARGET = process.env.npm_lifecycle_event;

const PATHS = {
    app: path.join(__dirname, '../client/'),
    build: path.join(__dirname, '../client/dist'),
};

const VENDOR = [
    // 'history',
    'babel-polyfill',
    'react',
    'react-dom',
    'react-redux',
    // 'react-router',
    'react-mixin',
    // 'classnames',
    'redux',
    // 'react-router-redux',
    'jquery',
];

process.env.BABEL_ENV = TARGET;

const common = {
    entry: {
        app: PATHS.app,
        vendor: VENDOR,
    },

    output: {
        filename: '[name].[hash].js',
        path: PATHS.build,
        publicPath: '/static'
    },

    plugins: [
        // new HtmlWebpackPlugin({
        //     template: path.join(__dirname, '../src/static/index.html'),
        //     hash: true,
        //     filename: 'index.html',
        //     inject: 'body'
        // }),
        new webpack.ProvidePlugin({
            '$': 'jquery',
            'jQuery': 'jquery',
            'window.jQuery': 'jquery'
        }),
        // extract all common modules to vendor so we can load multiple apps in one page
        new webpack.optimize.CommonsChunkPlugin({ name: 'vendor', filename: 'vendor.[hash].js' }),
        new CleanWebpackPlugin([PATHS.build], {
            root: process.cwd()
        })
    ],

    resolve: {
        extensions: ['', '.jsx', '.js', '.json'],
        modulesDirectories: ['node_modules', PATHS.app],
    },

    module: {
        loaders: [
            {
                test: /\.js$/,
                loaders: ['babel-loader'],
                exclude: /node_modules/,
            }
        ]
    },

    // sassLoader: {
    //     data: `@import "${__dirname}/../src/static/styles/config/_variables.scss";`
    // },

    // postcss: (param) => {
    //     return [
    //         autoprefixer({
    //             browsers: ['last 2 versions']
    //         }),
    //         postcssImport({
    //             addDependencyTo: param
    //         }),
    //     ];
    // },
};

if (TARGET === 'dev' || !TARGET) {
    module.exports = merge(development, common);
}

if (TARGET === 'prod' || !TARGET) {
    module.exports = merge(production, common);
}
