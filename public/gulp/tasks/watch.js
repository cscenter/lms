import gulp from "gulp";

import css from "./css";
import { reload } from "./server";
import { path } from "../configs";

export default function watch() {
    global.watch = true;

    // Modules styles
    gulp.watch(path.watch.scss, gulp.series(css));

    gulp.watch(path.watch.jinja2, reload);
}
