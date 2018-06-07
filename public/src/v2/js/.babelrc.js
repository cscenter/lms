var env = process.env.BABEL_ENV || process.env.NODE_ENV;
var plugins = [
    "@babel/plugin-proposal-object-rest-spread",
    "@babel/syntax-object-rest-spread",
    "transform-es2015-spread",
    // Allow class constants
    [
        "transform-class-properties",
        {
            "spec": true
        }
    ]
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

module.exports = {
    presets: [
        [
            "@babel/preset-stage-2",
            {
                "decoratorsLegacy": true
            }
        ],
        [
            "@babel/preset-env",
            {
                // FIXME: specify targets
                "modules": false,
                "useBuiltIns": false,
                "loose": true
            }
        ],
        "@babel/preset-react"
    ],
    plugins: plugins,
    // cacheDirectory: true,
};