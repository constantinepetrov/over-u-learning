import { createRequire } from "node:module";
import { copyFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { localizationPlugin } from "./localization-plugin.mjs";
const frontend =
  resolve(
    process.env.OVER_U_LMS_FRONTEND ||
      fileURLToPath(new URL("../../frontend/", import.meta.url)),
  ) + "/";
const requireFrontend = createRequire(frontend + "package.json");
const { build } = await import(
  pathToFileURL(dirname(requireFrontend.resolve("vite")) + "/dist/node/index.js"),
);
process.chdir(frontend);
await build({
  root: frontend,
  base: "/assets/lms/frontend/",
  configFile: frontend + "vite.config.js",
  plugins: [localizationPlugin()],
});
copyFileSync(
  frontend + "../lms/public/frontend/index.html",
  frontend + "../lms/www/_lms.html",
);
