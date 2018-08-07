var env = process.env.BABEL_ENV || process.env.NODE_ENV;
var plugins = [
    "@babel/plugin-proposal-object-rest-spread",
    "@babel/syntax-object-rest-spread",
    // FIXME: `transform-class-properties` included with preset-stage-2, but without spec=True. How to deal with it?
    // Allow class constants
    // ["transform-class-properties", {"spec": true}]
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
        "transform-es2015-modules-commonjs",
        "dynamic-import-node"
    ])
}


module.exports = {
    presets: [
        [
            "@babel/preset-env",
            {
                modules: false,
                useBuiltIns: false,
                debug: true,
                loose: true,
                spec: true,
                targets: {
                    browsers: [
                        "last 1 major version",
                        ">= 1%",
                        "Chrome >= 45",
                        "Firefox >= 38",
                        "Edge >= 12",
                        "Explorer >= 10",
                        "iOS >= 9",
                        "Safari >= 9",
                        "Android >= 4.4",
                        "Opera >= 30"

                    ]
                },
            }
        ],
        [
            "@babel/preset-stage-2",
            {
                "decoratorsLegacy": true
            }
        ],
        "@babel/preset-react"
    ],
    plugins: plugins,
    // cacheDirectory: true,
};