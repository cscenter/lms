import errorHandler from "./utils/errorHandler";
import autoprefixer from "autoprefixer";
import path from "path";

const staticVersion = process.env.APP_VERSION || "v2";

export const rootDir = path.dirname(__dirname);

export const paths = {
    build: {
        css: `assets/${staticVersion}/dist/css/`,
        img: `assets/${staticVersion}/dist/img/`,
        svgSprites: `assets/${staticVersion}/dist/img/sprites/`,
        svgSpritesSCSS: `src/${staticVersion}/scss/sprites/`,
    },
    src: {
        scss: `src/${staticVersion}/scss/`,
        img: `src/${staticVersion}/img/`,
        svgSprites: `src/${staticVersion}/img/sprites/svg/`,
        // js managed by webpack, ok
    },
    watch: {
        jinja2: `templates/${staticVersion}/**/*.jinja2`,
        scss: `src/${staticVersion}/scss/**/*.scss`,
        img: `src/${staticVersion}/img/**/*.*`,
        fonts: `src/${staticVersion}/fonts/**/*.*`
    },
    clean: {
        css: `./assets/${staticVersion}/dist/**/*.css`
    }
};

export const sassConfig = {
    outputStyle: 'compressed',
    includePaths: ['./node_modules/']
};


export let postCssPlugins;
if (staticVersion === "v2") {
    postCssPlugins = [
        autoprefixer({
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
        })
    ];
} else {
    postCssPlugins = [
        autoprefixer({
            browsers: [
                'Chrome >= 45',
                'Firefox ESR',
                'Edge >= 12',
                'Explorer >= 10',
                'iOS >= 9',
                'Safari >= 9',
                'Android >= 4.4',
                'Opera >= 30'
            ]
        })
    ];
}

export const plumberConfig = {
    errorHandler
};

let PROXY_PORT = 8000;
export const browserSyncConfig = {
    proxy: `localhost:${PROXY_PORT}`,
    notify: false,
    reloadOnRestart: true,
    snippetOptions: {
        rule: {
            match: /<\/body>/i
        }
    }
};

// Cleanup configuration
export const delConfig = [paths.clean.css, paths.build.svgSprites];