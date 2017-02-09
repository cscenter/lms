const path = require('path');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const merge = require('webpack-merge');  // merge webpack configs
const CleanWebpackPlugin = require('clean-webpack-plugin');  // clean build dir before building

const development = require('./dev.config');
const production = require('./prod.config');

// require('babel-polyfill').default; FIXME: wtf?

const TARGET = process.env.npm_lifecycle_event;
process.env.BABEL_ENV = TARGET;

const __assetsdir = path.join(__dirname, '../cscsite/assets');

const PATHS = {
    common: path.join(__assetsdir, '/src/js/main.js'),
    profile: path.join(__assetsdir, '/src/js/profile.js'),
    dist: path.join(__assetsdir, '/js/dist'),
};

const VENDOR = [
    // 'history',
    // 'babel-polyfill',
    // 'react',
    // 'react-dom',
    // 'react-redux',
    // 'react-router',
    // 'react-mixin',
    // 'classnames',
    // 'redux',
    // 'react-router-redux',
    // 'jquery',
    // 'bootstrap-sass',
];

const common = {
    context: path.resolve(__dirname, ".."),

    entry: {
        main: PATHS.common,
        profile: PATHS.profile,
        // vendor: VENDOR,
    },

    output: {
        filename: '[name]-[hash].js',
        path: PATHS.dist,
    },

    externals: {
        jquery: 'jQuery',
        // Note: EpicEditor is an old dead shit without correct support.
        EpicEditor: 'EpicEditor'
    },

    plugins: [
        new BundleTracker({filename: './webpack/webpack-stats.json'}),
        // TODO: Prevent autoload jquery for now
        // new webpack.ProvidePlugin({
        //     '$': 'jquery',
        //     'jQuery': 'jquery',
        //     'window.jQuery': 'jquery'
        // }),
        // extract all common modules to vendor so we can load multiple apps in one page
        new webpack.optimize.CommonsChunkPlugin({
            name: 'vendor',
        }),
        new CleanWebpackPlugin([PATHS.dist], {
            verbose: true,
            root: process.cwd()
        })
    ],

    resolve: {
        extensions: ['.jsx', '.js'],
        modules: [
            path.join(__assetsdir, '/src/js'),
            'node_modules',
        ],
    },

    module: {
        // noParse: [/bootstrap-sweetalert/],
        loaders: [
            {
                test: /\.js$/,
                loaders: ['babel-loader'],
                exclude: '/node_modules/',
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

if (['dev', 'start'].includes(TARGET) || !TARGET) {
    module.exports = merge(common, development);
}

if (TARGET === 'prod' || !TARGET) {
    module.exports = merge(common, production);
}
