import gulp from "gulp";

import css from "./css";
import { reload } from "./server";
import { paths } from "../configs";
import svgSprites from "./svgSprites";

export default function watch() {
    global.watch = true;

    // Modules styles
    gulp.watch(paths.watch.scss, gulp.series(css));

    gulp.watch(paths.src.svgSprites, gulp.series(svgSprites));

    gulp.watch(paths.watch.jinja2, reload);
}
