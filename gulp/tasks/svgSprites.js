import gulp from "gulp";
import plumber from "gulp-plumber";
import gulpif from "gulp-if";
import svgSprite from "gulp-svg-sprite";
import svgmin from "gulp-svgmin";
import cheerio from "gulp-cheerio";
import filter from "gulp-filter";
import path from "path";
import {rootDir, paths, plumberConfig} from "../configs";
import getDirs from "../utils/getDirs";
import createEmptyStream from "../utils/emptyStream";
import merge from "merge-stream";  // combines the streams and ends only when all streams emitted end


// https://github.com/gulpjs/gulp/blob/4.0/docs/recipes/running-task-steps-per-folder.md
const svgSprites = () => {
    let sprites = getDirs(paths.src.svgSprites);
    if (sprites.length == 0) {
        return createEmptyStream();
    }

    // Executes the function once per dir, and returns the async stream
    let tasks = sprites.map(function (dir) {
        return gulp.src(["*.svg"], {cwd: paths.src.svgSprites + dir})
            .pipe(plumber(plumberConfig))
            // TODO: What if gulp-svg-spirets optimize svg?
            // .pipe(gulpif(global.watch !== true, svgmin({
            // 	js2svg: {
            // 		pretty: true
            // 	}
            // })))
            // remove all fill and style declarations in out shapes
            // .pipe(cheerio({
            // 	run: function ($) {
            // 		$('[fill]').removeAttr('fill');
            // 		$('[style]').removeAttr('style');
            // 	},
            // 	parserOptions: { xmlMode: true }
            // }))
            // build svg sprite
            .pipe(svgSprite({
                // svg: {namespaceClassnames: false},
                mode: {
                    defs: {
                        dest: '.',
                        sprite: path.join(paths.build.svgSprites, `${dir}.svg`),
                        prefix: "._%s",
                        dimensions: "%s",
                        bust: false,
                        example: false,
                        render: {
                            scss: {
                                dest: path.join(paths.build.svgSpritesSCSS, `_${dir}.scss`),
                            },
                        }
                    }
                },
            }))
            .pipe(gulp.dest(rootDir));
    });
    return merge(tasks);
};

export default svgSprites;

gulp.task('svg-sprites', svgSprites);