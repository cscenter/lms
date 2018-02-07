import gulp from "gulp";
import plumber from "gulp-plumber";
import cached from "gulp-cached";
import sass from "gulp-sass";
import sassInheritance from "gulp-sass-inheritance";
import postcss from "gulp-postcss";
import gulpif from "gulp-if";
import filter from "gulp-filter";

import { postCssPlugins, sassConfig, plumberConfig, path } from "../configs";
import bs from "../utils/getBrowserSyncInstance";

const css = () =>
    gulp
        .src(["**/*.scss"], {cwd: path.src.scss})
        .pipe(plumber(plumberConfig))
        //filter out unchanged scss files, only works when watching
        .pipe(gulpif(global.watch, cached('sass')))
        //find files that depend on the files that have changed
        .pipe(sassInheritance({dir: path.src.scss}))
        //filter out internal imports (folders and files starting with "_" )
        .pipe(filter(function (file) {
          return !/\/_/.test(file.path) || !/^_/.test(file.basename);
        }))
        .pipe(sass(sassConfig).on('error', sass.logError))
        .pipe(postcss(postCssPlugins))
        .pipe(gulp.dest(path.build.css))
        .pipe(bs.reload({
            stream: true
        }));

export default css;