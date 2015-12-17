var path = require("path")
var webpack = require('webpack')
var BundleTracker = require('webpack-bundle-tracker')

module.exports = {
    context: __dirname,

    entry: './cscsite/assets/js/index.jsx',

    output: {
        path: path.resolve('./cscsite/assets/bundles/'),
        filename: "[name]-[hash].js"
    },

    plugins: [], // add all common plugins here

    module: {
        loaders: [] // add all common loaders here
    },

    externals: {
        // get it from a global 'React' variable
        'react': 'React'
    },

    resolve: {
        modulesDirectories: ['node_modules', 'bower_components'],
        extensions: ['', '.js', '.jsx']
    },
}