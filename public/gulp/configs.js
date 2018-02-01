import errorHandler from "./utils/errorHandler";

export const path = {
    build: {
        css: 'assets/v2/dist/css/',
        img: 'assets/v2/dist/img/',
    },
    src: {
        scss: 'src/v2/scss/',
        img: 'src/v2/img/',
    },
    watch: {
        jinja2: 'app/templates/v2/**/*.jinja2',
        scss: 'src/v2/scss/**/*.scss',
        img: 'src/v2/img/**/*.*',
        fonts: 'src/v2/fonts/**/*.*'
    },
    clean: './assets/v2/dist'
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