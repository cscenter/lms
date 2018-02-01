import del from "del";

import { delConfig } from "../configs";

const cleanup = callback => del(delConfig, callback);

export default cleanup;