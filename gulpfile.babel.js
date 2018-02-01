import { task, series } from "gulp";
import build from "./gulp/tasks/build";
import dev from "./gulp/tasks/dev";

// Main tasks
task("build", build);
task("dev", dev);

// Default task
task("default", series("dev"));
