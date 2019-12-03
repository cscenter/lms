var env = process.env.BABEL_ENV || process.env.NODE_ENV;
var plugins = [
    "@babel/plugin-proposal-object-rest-spread",
    "@babel/syntax-object-rest-spread",
    // Stage 2
    ["@babel/plugin-proposal-decorators", {"legacy": true}],
    "@babel/plugin-proposal-function-sent",
    "@babel/plugin-proposal-export-namespace-from",
    "@babel/plugin-proposal-numeric-separator",
    "@babel/plugin-proposal-throw-expressions",
    // Stage 3
    "@babel/plugin-syntax-dynamic-import",
    "@babel/plugin-syntax-import-meta",
    ["@babel/plugin-proposal-class-properties", {"loose": false}],
    "@babel/plugin-proposal-json-strings"
];
if (env === 'production') {
    plugins.push.apply(plugins, [
        ["transform-react-remove-prop-types", {
            // TODO: eslint-plugin-react has a rule forbid-foreign-prop-types to make this plugin safer
            "mode": "remove",
            "removeImport": true,
            // "ignoreFilenames": ["node_modules"]
        }]
    ])
}

if (env === 'test') {
    plugins.push.apply(plugins, [
        "@babel/plugin-transform-modules-commonjs",
        "dynamic-import-node"
    ])
}

module.exports = {
    presets: [
        [
            "@babel/preset-env",
            {
                modules: false,
                useBuiltIns: "usage",
                corejs: 3,
                debug: true,
                loose: true,
                spec: true,
            }
        ],
        "@babel/typescript",
        "@babel/preset-react"
    ],
    plugins: plugins,
    // cacheDirectory: true,
};