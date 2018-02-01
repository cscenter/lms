import { series } from "gulp";

import cleanup from "./cleanup";
import css from "./css";

const build = series(
  cleanup,
  css
);

export default build;