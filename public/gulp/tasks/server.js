import browserSync from "../utils/getBrowserSyncInstance";
import { browserSyncConfig } from "../configs";

export const server = () => browserSync.init(browserSyncConfig);

export const reload = calback => {
  browserSync.reload();
  calback();
};