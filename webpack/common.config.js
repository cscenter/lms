const path = require('path');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const merge = require('webpack-merge');  // merge webpack configs
const CleanWebpackPlugin = require('clean-webpack-plugin');  // clean build dir before building
const ExtractTextPlugin = require('extract-text-webpack-plugin');

const DEBUG = (process.env.NODE_ENV !== "production");

const extractScss = new ExtractTextPlugin({
    filename: "[name].[contenthash].css",
    allChunks: true,
    disable: DEBUG
});

const development = require('./dev.config');
const production = require('./prod.config');
const TARGET = process.env.npm_lifecycle_event;

// require('babel-polyfill').default; FIXME: wtf?

process.env.BABEL_ENV = TARGET;

const __assetsdir = path.join(__dirname, '../cscsite/assets');
const __nodemodulesdir = path.join(__dirname, '../node_modules');
let bundlesDirRelative = './js/dist/';
// All dependencies will be copied to path, relative to bundles output
const STATIC_PATH = path.join('/static/', bundlesDirRelative);
const STATIC_URL = path.join('/static/');

// TODO: analyze bundles size and concat
const PATHS = {
    common: path.join(__assetsdir, '/src/js/main.js'),
    profile: path.join(__assetsdir, '/src/js/profile.js'),
    forms: path.join(__assetsdir, '/src/js/forms.js'),
    admission: path.join(__assetsdir, '/src/js/center/admission.js'),
    supervising: path.join(__assetsdir, '/src/js/supervising/index.js'),
    learning: path.join(__assetsdir, '/src/js/learning/index.js'),
    teaching: path.join(__assetsdir, '/src/js/teaching/index.js'),
    dist: path.join(__assetsdir, bundlesDirRelative),
    stats: path.join(__assetsdir, "/src/js/stats/main.js"),
    center_styles: path.join(__assetsdir, "/src/sass/center/index.js"), // import common here?
    club_styles: path.join(__assetsdir, "/src/sass/club/index.js"),
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
    path.join(__assetsdir, '/src/js/editor.js'),
];

const common = {
    context: __assetsdir,

    entry: {
        center_styles: PATHS.center_styles,
        club_styles: PATHS.club_styles,
        main: PATHS.common,
        profile: PATHS.profile,
        forms: PATHS.forms, // TODO: Should it be DLL instead?
        admission: PATHS.admission,
        learning: PATHS.learning,
        teaching: PATHS.teaching,
        stats: PATHS.stats,
        supervising: PATHS.supervising,
        vendor: VENDOR,
    },

    output: {
        filename: '[name]-[hash].js',
        path: PATHS.dist,
    },

    externals: {
        jquery: 'jQuery',
        // Note: EpicEditor is an old dead shit without correct support.
        EpicEditor: 'EpicEditor',
        "d3": "d3"
    },

    resolve: {
        extensions: ['.jsx', '.js'],
        modules: [
            path.join(__assetsdir, '/src/js'),
            __nodemodulesdir,
        ],
        symlinks: false
    },

    module: {
        rules: [
            {
                test: /\.js$/,
                use: [
                    {
                        loader: 'babel-loader',
                        options: {
                            cacheDirectory: true  // Improve performance
                        }
                    }
                ],
                include: path.resolve(__assetsdir, "src/js"),
                exclude: [
                    path.resolve(__assetsdir, "src/js/center/index.js"),
                    path.resolve(__assetsdir, "src/js/club/index.js"),
                ]
            },
            {
                test: /\.scss$/,
                exclude: __nodemodulesdir,
                use: extractScss.extract({
                    fallback: 'style-loader', // inject CSS to page
                    use: [
                        {
                            loader: 'css-loader', // translates CSS into CommonJS modules
                            options: {
                                minimize: !DEBUG,
                                sourceMap: DEBUG,
                            }
                        },
                        {
                            loader: 'postcss-loader', // Run post css actions
                            options: {
                                // ident: 'postcss',
                                sourceMap: DEBUG,
                                // config: {
                                //     path: path.join(__dirname, '../postcss.config.js')
                                // },
                                // plugins: () => { // post css plugins, can be exported to postcss.config.js
                                //     return [
                                //         require('autoprefixer')
                                //     ];
                                // }
                            }
                        },
                        {
                            // All urls must be relative to the entry-file, workaround for this
                            // More about this problem: https://github.com/webpack-contrib/sass-loader#problems-with-url
                            loader: 'resolve-url-loader',
                            options: {
                                sourceMap: DEBUG
                            }
                        },
                        {
                            loader: 'sass-loader', // compiles SASS to CSS
                            options: {
                                sourceMap: true, // need this for `resolve-url-loader`
                                outputStyle: 'expanded',
                                includePaths: [__nodemodulesdir,]
                            }
                        },
                    ]
                }),
            },
            {
                test: /\.woff2?$|\.ttf$|\.eot$|\.svg|\.png|\.jpg$/,
                exclude: __nodemodulesdir,
                use: [{
                    loader: "file-loader",
                    options: {
                        // context: __nodemodulesdir,
                        name: '[path][name].[ext]',
                        emitFile: false, // since all images are in assets/img dir, do not copy paste it, use publicPath instead
                        publicPath: STATIC_URL
                    }
                }]
            },
            {
                test: /\.swf$/,
                include: __nodemodulesdir,
                use: [
                    {
                        loader: 'file-loader',
                        options: {
                            context: __nodemodulesdir,
                            publicPath: STATIC_PATH,
                            name: '[path][name].[ext]'
                        }
                    }
                ],
            },
        ]
    },

    plugins: [
        new webpack.optimize.ModuleConcatenationPlugin(),
        new BundleTracker({filename: './webpack/webpack-stats.json'}),
        // Fixes warning in moment-with-locales.min.js
        //   Module not found: Error: Can't resolve './locale' in ...
        new webpack.IgnorePlugin(/^\.\/locale$/),
        // TODO: Prevent autoload jquery for now
        // new webpack.ProvidePlugin({
        //     '$': 'jquery',
        //     'jQuery': 'jquery',
        //     'window.jQuery': 'jquery'
        // }),
        // extract all common modules to vendor so we can load multiple apps in one page
        new webpack.optimize.CommonsChunkPlugin({
            name: "vendor"
        }),
        new webpack.optimize.CommonsChunkPlugin({
            name: "manifest",
            minChunks: Infinity
        }),
        new CleanWebpackPlugin([PATHS.dist], {
            verbose: true,
            root: process.cwd()
        }),
        extractScss,
    ],
};

if (['dev', 'start'].includes(TARGET) || !TARGET) {
    module.exports = merge(common, development);
}

if (TARGET === 'prod' || !TARGET) {
    module.exports = merge(common, production);
}
