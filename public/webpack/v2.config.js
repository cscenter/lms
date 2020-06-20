const path = require('path');
const webpack = require('webpack');
const merge = require('webpack-merge');  // merge webpack configs
const { CleanWebpackPlugin } = require('clean-webpack-plugin');  // clean build dir before building
const Dotenv = require('dotenv-webpack');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");


const DEBUG = (process.env.NODE_ENV !== "production");
const LOCAL_BUILD = (process.env.LOCAL_BUILD === "1");

const development = require('./dev.config');
const production = require('./prod.config');
const localConfiguration = require('./local.config');

process.env.BABEL_ENV = process.env.NODE_ENV;

const APP_VERSION = "v2";

const __srcdir = path.join(__dirname, `../src/${APP_VERSION}`);
const __nodemodulesdir = path.join(__dirname, '../node_modules');

// All dependencies will be copied to path, relative to bundles output
const STATIC_URL = path.join('/static/');

const PATHS = {
    common: path.join(__srcdir, '/js/main.js'),
};


const common = {

    context: __srcdir,

    entry: {
        common: [
            // "core-js/stable",
            // "regenerator-runtime/runtime",
            //'jquery',
            'ky',
            'popper.js',
            'fontfaceobserver',
            'noty',
        ],
        main: PATHS.common,
    },

    output: {
        filename: '[name]-[hash].js',
    },

    externals: {},

    resolve: {
        extensions: ['.jsx', '.js', '.ts', '.tsx'],
        modules: [
            path.join(__srcdir, '/js'),
            __nodemodulesdir
        ],
        symlinks: false
    },

    module: {
        rules: [
            {
                test: /bootstrap\.native/,
                use: {
                    loader: 'bootstrap.native-loader',
                    options: {
                        bs_version: 4,
                        only: [
                            'collapse',
                            'dropdown',
                        ]
                    }
                }
            },
            {
                test: /\.(js|jsx|ts|tsx)$/,
                include: path.resolve(__srcdir, "js"),
                use: [
                    {loader: 'babel-loader'},
                    {loader: 'eslint-loader'},
                ]
            },
            {
                test: /\.(js|jsx|ts|tsx)$/,
                include: [
                    path.resolve(__nodemodulesdir, "ky"),
                    path.resolve(__nodemodulesdir, "bootstrap"),
                    path.resolve(__nodemodulesdir, "react-async"),
                    path.resolve(__nodemodulesdir, "react-hook-form"),
                ],
                use: [{
                    loader: 'babel-loader',
                    options: {
                        extends: path.resolve(__srcdir, "js", ".babelrc.js"),
                        cacheDirectory: false,
                    }
                }]
            },
            {
                test: /\.s?[ac]ss$/,
                exclude: __nodemodulesdir,
                use: [
                    {
                        loader: MiniCssExtractPlugin.loader,
                        options: {
                            hmr: DEBUG,
                        },
                    },
                    {
                        loader: 'css-loader', // translates CSS into CommonJS modules
                        options: {
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
                            sassOptions: {
                                // precision: 8,
                                includePaths: [__nodemodulesdir,]
                            }
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
            // Static in a project source directory
            {
                test: /\.woff2?$|\.ttf$|\.eot$|\.svg|\.png|\.jpg$/,
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
        ]
    },

    plugins: [
        new Dotenv({
            path: path.join(__dirname, '.env'),
            silent: true,
        }),
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
            chunks: "async",
            minSize: 30000,
            minChunks: 2,
            maxAsyncRequests: 6,
            maxInitialRequests: 4,
            automaticNameDelimiter: '~',
            automaticNameMaxLength: DEBUG ? 109 : 30,
            // name: true,
            cacheGroups: {
                common: {
                    chunks: "all",
                    test: /(common|[\\/]node_modules[\\/]core-js[\\/])/,
                    name: "common",
                    enforce: true
                },
                // react: {
                //     chunks: "all",
                //     test: /[\\/]node_modules[\\/](react|react-dom)[\\/]/,
                //     name: "react",
                //     enforce: true,
                // },
                vendors: {
                    // chunks: "all",
                    minChunks: 5,
                    test: /[\\/]node_modules[\\/]/,
                    priority: -10,
                    // name: "vendors"
                    // reuseExistingChunk: true
                },
                // default: {
                //     minChunks: 2,
                //     priority: -20,
                //     reuseExistingChunk: true
                // }
            }
        }
    }

};

let appConfig;
if (process.env.NODE_ENV !== "development") {
    let configs = [common, production];
    if (LOCAL_BUILD) {
        configs.push(localConfiguration);
    }
    appConfig = merge(configs);
} else {
    appConfig = merge(common, development);
}

module.exports = appConfig;