import errorHandler from "./utils/errorHandler";

const staticVersion = process.env.STATIC_VERSION || "v2";

export const path = {
    build: {
        css: `assets/${staticVersion}/dist/css/`,
        img: `assets/${staticVersion}/dist/img/`,
    },
    src: {
        scss: `src/${staticVersion}/scss/`,
        img: `src/${staticVersion}/img/`,
    },
    watch: {
        jinja2: `app/templates/${staticVersion}/**/*.jinja2`,
        scss: `src/${staticVersion}/scss/**/*.scss`,
        img: `src/${staticVersion}/img/**/*.*`,
        fonts: `src/${staticVersion}/fonts/**/*.*`
    },
    clean: `./assets/${staticVersion}/dist`
};

export const sassConfig = {
    outputStyle: 'compressed',
    includePaths: ['./node_modules/']
};

export const autoprefixerBrowserSupport = [
    'Chrome >= 45',
    'Firefox ESR',
    'Edge >= 12',
    'Explorer >= 10',
    'iOS >= 9',
    'Safari >= 9',
    'Android >= 4.4',
    'Opera >= 30'
];

export const plumberConfig = {
    errorHandler
};

export const browserSyncConfig = {
    proxy: "localhost:8001",
    notify: false,
    reloadOnRestart: true,
    snippetOptions: {
        rule: {
            match: /<\/body>/i
        }
    }
};

// Cleanup configuration
export const delConfig = [path.clean];