import { task, series } from "gulp";
import build from "./tasks/build";
import dev from "./tasks/dev";

// Main tasks
task("build", build);
task("dev", dev);

// Default task
task("default", series("dev"));
