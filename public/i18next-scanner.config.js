const fs = require('fs');
const chalk = require('chalk');
const eol = require('eol');
const path = require('path');
const VirtualFile = require('vinyl');


function flush(done) {
    const {parser} = this;
    const {options} = parser;

    // Flush to resource store
    const resStore = parser.get({sort: options.sort});
    const {jsonIndent} = options.resource;
    const lineEnding = String(options.resource.lineEnding).toLowerCase();

    Object.keys(resStore).forEach((lng) => {
        const namespaces = resStore[lng];

        Object.keys(namespaces).forEach((ns) => {
            const resPath = parser.formatResourceSavePath(lng, ns);
            let resContent;
            try {
                resContent = JSON.parse(
                    fs.readFileSync(
                        fs.realpathSync(path.join('assets', 'v2', 'js', 'locales', resPath))
                    ).toString('utf-8')
                );
            } catch (e) {
                resContent = {};
            }
            const obj = {...namespaces[ns], ...resContent};
            let text = JSON.stringify(obj, null, jsonIndent) + '\n';

            if (lineEnding === 'auto') {
                text = eol.auto(text);
            } else if (lineEnding === '\r\n' || lineEnding === 'crlf') {
                text = eol.crlf(text);
            } else if (lineEnding === '\n' || lineEnding === 'lf') {
                text = eol.lf(text);
            } else if (lineEnding === '\r' || lineEnding === 'cr') {
                text = eol.cr(text);
            } else { // Defaults to LF
                text = eol.lf(text);
            }

            let contents = null;

            try {
                // "Buffer.from(string[, encoding])" is added in Node.js v5.10.0
                contents = Buffer.from(text);
            } catch (e) {
                // Fallback to "new Buffer(string[, encoding])" which is deprecated since Node.js v6.0.0
                contents = new Buffer(text);
            }

            this.push(new VirtualFile({
                path: resPath,
                contents: contents
            }));
        });
    });

    done();
}

module.exports = {
    input: [
        'src/v2/js/**/*.{js,jsx}',
        // Use ! to filter out files or directories
        '!**/node_modules/**',
    ],
    output: './assets/v2/js/locales/',
    options: {
        debug: true,
        func: {
            list: ['i18next.t', 'i18n.t', 't'],
            extensions: ['.js', '.jsx']
        },
        trans: {
            component: 'Trans',
            i18nKey: 'i18nKey',
            defaultsKey: 'defaults',
            extensions: ['.jsx'],
            fallbackKey: function (ns, value) {
                return value;
            },
            acorn: {
                ecmaVersion: 10, // defaults to 10
                sourceType: 'module', // defaults to 'module'
                // Check out https://github.com/acornjs/acorn/tree/master/acorn#interface for additional options
            }
        },
        lngs: ['en', 'ru'],
        ns: [
            'translation'
        ],
        defaultLng: 'ru',
        defaultNs: 'translation',
        defaultValue: function (lng, ns, key) {
            if (lng === 'ru') {
                // Return key as the default value for Russian language
                return key;
            }
            // Empty string for other languages
            return '';
        },
        resource: {
            loadPath: '{{lng}}/{{ns}}.json',
            savePath: '{{lng}}/{{ns}}.json',
            jsonIndent: 2,
            lineEnding: '\n'
        },
        nsSeparator: false, // namespace separator
        keySeparator: false, // key separator
        interpolation: {
            prefix: '{{',
            suffix: '}}'
        }
    },
    transform: function customTransform(file, enc, done) {
        "use strict";
        const parser = this.parser;
        const content = fs.readFileSync(file.path, enc);
        let count = 0;

        parser.parseFuncFromString(content, {list: ['i18next._', 'i18next.__']}, (key, options) => {
            parser.set(key, Object.assign({}, options, {
                nsSeparator: false,
                keySeparator: false
            }));
            ++count;
        });

        if (count > 0) {
            console.log(`i18next-scanner: count=${chalk.cyan(count)}, file=${chalk.yellow(JSON.stringify(file.relative))}`);
        }

        done();
    },
    flush,
};