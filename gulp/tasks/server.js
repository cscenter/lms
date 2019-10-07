import browserSync from "../utils/getBrowserSyncInstance";
import { browserSyncConfig } from "../configs";

export const server = () => browserSync.init(browserSyncConfig);

export const reload = callback => {
  browserSync.reload();
  callback();
};