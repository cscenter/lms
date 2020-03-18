const path = require('path');
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const merge = require('webpack-merge');  // merge webpack configs
const { CleanWebpackPlugin } = require('clean-webpack-plugin');  // clean build dir before building
const Dotenv = require('dotenv-webpack');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const DEBUG = (process.env.NODE_ENV !== "production");


const development = require('./dev.config');
const production = require('./prod.config');
const TARGET = process.env.npm_lifecycle_event;

process.env.BABEL_ENV = process.env.NODE_ENV;

const APP_VERSION = "v1";

const __srcdir = path.join(__dirname, `../src/${APP_VERSION}`);
const __nodemodulesdir = path.join(__dirname, '../node_modules');
let __bundlesdir = path.join(__dirname, `../assets/${APP_VERSION}/dist/js`);

// All dependencies will be copied to path, relative to bundles output
const STATIC_URL = path.join('/static/');

// TODO: analyze bundles size and concat
const PATHS = {
    common: path.join(__srcdir, '/js/main.js'),
    admission: path.join(__srcdir, '/js/center/admission/index.js'),
    supervising: path.join(__srcdir, '/js/supervising/index.js'),
    learning: path.join(__srcdir, '/js/learning/index.js'),
    teaching: path.join(__srcdir, '/js/teaching/index.js'),
    stats: path.join(__srcdir, "/js/stats/main.js"),
    center: path.join(__srcdir, "/js/center/index.js"),
    club: path.join(__srcdir, "/js/club/index.js"),
};


const VENDOR = [
    "core-js/stable",
    "regenerator-runtime/runtime",
    path.join(__srcdir, '/js/components/editor'),
];

const common = {
    context: __srcdir,

    entry: {
        main: PATHS.common,
        center: PATHS.center,
        club: PATHS.club,
        admission: PATHS.admission,
        learning: PATHS.learning,
        teaching: PATHS.teaching,
        stats: PATHS.stats,
        supervising: PATHS.supervising,
        vendor: VENDOR,
    },

    output: {
        filename: '[name]-[hash].js',
        path: __bundlesdir,
    },

    externals: {
        jquery: 'jQuery',
        // Note: EpicEditor is an old dead shit without correct support.
        EpicEditor: 'EpicEditor',
    },

    resolve: {
        extensions: ['.jsx', '.js'],
        modules: [
            path.join(__srcdir, '/js'),
            __nodemodulesdir
        ],
        symlinks: false
    },

    module: {
        rules: [
            {
                test: /\.(js|jsx)$/,
                use: [
                    {
                        loader: 'babel-loader',
                    }
                ],
                include: path.resolve(__srcdir, "js")
            },
            {
                test: /\.s?[ac]ss$/,
                exclude: __nodemodulesdir,
                use: [
                    DEBUG ? 'style-loader' : MiniCssExtractPlugin.loader,
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
                            // See `postcss.config.js` for details
                            sourceMap: DEBUG,
                        }
                    },
                    {
                        loader: 'sass-loader', // compiles SASS to CSS
                        options: {
                            sourceMap: DEBUG,
                            outputStyle: 'expanded',
                            includePaths: [__nodemodulesdir,]
                        }
                    },
                ],
            },
            {
                test: /\.css$/,
                use: [
                    DEBUG ? 'style-loader' : MiniCssExtractPlugin.loader,
                    'css-loader',
                ],
            },
            // Static in a project source directory
            {
                test: /\.woff2?$|\.ttf$|\.eot$|\.svg$|\.png$|\.jpg$|\.swf$/,
                exclude: __nodemodulesdir,
                use: [{
                    loader: "file-loader",
                    options: {
                        name: '[path][name].[ext]',
                        emitFile: false, // since all images are in assets/img dir, do not copy paste it, use publicPath instead
                        // FIXME: replace with __webpack_public_path__
                        publicPath: STATIC_URL,
                    }
                }]
            },
            // Serve static in node_modules/
            {
                test: /\.woff2?$|\.ttf$|\.eot$|\.svg$|\.png$|\.jpg$|\.swf$/,
                include: __nodemodulesdir,
                use: [{
                    loader: "file-loader",
                    options: {
                        context: __nodemodulesdir,
                        name: (file) => {
                            if (process.env.NODE_ENV === 'development') {
                                return `[path][name].[ext]`;
                            }

                            return '[path][contenthash].[ext]';
                        },
                        outputPath: 'assets',
                        publicPath: (url, resourcePath, context) => {
                            // `resourcePath` is original absolute path to asset
                            // `context` is a directory where asset is stored (`rootContext` or `context` option)
                            if (process.env.NODE_ENV === 'development') {
                                return `node_modules/${url}`;
                            }
                            return `assets/${url}`;
                        },
                        postTransformPublicPath: (p) => `__webpack_public_path__ + ${p}`,
                        emitFile: !DEBUG,
                    }
                }]
            },

        ]
    },

    plugins: [
        new Dotenv({
            path: path.join(__dirname, '.env'),
            silent: false,
        }),
        new BundleTracker({filename: './webpack-stats.json'}),
        // Fixes warning in moment-with-locales.min.js
        //   Module not found: Error: Can't resolve './locale' in ...
        new webpack.IgnorePlugin(/^\.\/locale$/),
        new CleanWebpackPlugin({
            verbose: true,
            cleanOnceBeforeBuildPatterns: ['**/*', '!.gitattributes'],
        }),
        new MiniCssExtractPlugin({
            // Options similar to the same options in webpackOptions.output
            // both options are optional
            filename: DEBUG ? '[name].css' : '[name].[hash].css',
            chunkFilename: DEBUG ? '[id].[name].css' : '[name]-[chunkhash].css',
        })
    ],

    optimization: {
        splitChunks: {
            minChunks: 2,
            cacheGroups: {
                vendor: {
                    name: "vendor",
                    test: "vendor",
                    enforce: true
                },
                forms: {
                    name: "forms",
                    test: "components/forms",
                    enforce: true
                },
            }
        }
    }
};

let appConfig;
if (process.env.NODE_ENV !== "development") {
    appConfig = merge(common, production);
} else {
    appConfig = merge(common, development);
}

module.exports = appConfig;