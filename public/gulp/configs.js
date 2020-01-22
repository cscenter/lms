import errorHandler from "./utils/errorHandler";
import autoprefixer from "autoprefixer";
import path from "path";

const staticVersion = process.env.APP_VERSION || "v2";

export const rootDir = path.dirname(__dirname);

export const paths = {
    build: {
        css: path.join(rootDir, `assets/${staticVersion}/dist/css/`),
        img: `assets/${staticVersion}/dist/img/`,
        svgSprites: `assets/${staticVersion}/dist/img/sprites/`,
        svgSpritesSCSS: `src/${staticVersion}/scss/sprites/`,
    },
    src: {
        scss: path.join(rootDir, `src/${staticVersion}/scss/`),
        img: path.join(rootDir, `src/${staticVersion}/img/`),
        svgSprites: path.join(rootDir, `src/${staticVersion}/img/sprites/svg/`),
        // js managed by webpack, ok
    },
    watch: {
        jinja2: path.join(rootDir, `templates/${staticVersion}/**/*.jinja2`),
        scss: path.join(rootDir, `src/${staticVersion}/scss/**/*.scss`),
        img: path.join(rootDir, `src/${staticVersion}/img/**/*.*`),
        fonts: path.join(rootDir, `src/${staticVersion}/fonts/**/*.*`)
    },
    clean: {
        css: path.join(rootDir, `assets/${staticVersion}/dist/css/**/*.css`),
        svgSprites: path.join(rootDir, `assets/${staticVersion}/dist/img/sprites/`),
    }
};


export const sassConfig = {
    outputStyle: 'compressed',
    includePaths: [
        './node_modules/',
        '../node_modules/',
    ]
};


export let postCssPlugins = [
    autoprefixer()
];

export const plumberConfig = {
    errorHandler
};

let proxyPort, i = process.argv.indexOf("--port");
if (i > -1) {
    proxyPort = process.argv[i + 1];
} else {
    proxyPort = 8000;
}

export const browserSyncConfig = {
    proxy: `localhost:${proxyPort}`,
    notify: false,
    reloadOnRestart: true,
    startPath: `/${staticVersion}/pages/`,
    snippetOptions: {
        rule: {
            match: /<\/body>/i
        }
    }
};

// Cleanup configuration
export const delConfig = [paths.clean.css, paths.clean.svgSprites];