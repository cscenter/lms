import fs from "fs";
import path from "path";

/**
 * Get array of directories names inside paths (no recursive)
 * @param paths
 * @returns {*}
 */

export default function getDirs(parentDir) {
    return fs.readdirSync(parentDir)
      .filter(function(file) {
        return fs.statSync(path.join(parentDir, file)).isDirectory();
      });
}