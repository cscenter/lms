import del from "del";

import { delConfig } from "../configs";

const cleanup = callback => del(delConfig, {force: true}, callback);

export default cleanup;