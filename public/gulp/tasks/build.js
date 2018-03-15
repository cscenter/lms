import { series, parallel } from "gulp";

import cleanup from "./cleanup";
import svgSprites from "./svgSprites";
import css from "./css";

const build = series(
  cleanup,
  parallel(css, svgSprites)
);

export default build;