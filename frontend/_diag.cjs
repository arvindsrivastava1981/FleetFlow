const fs = require("fs");
const file = "C:/Personal/projects/FleetFlow/frontend/src/pages/Onboarding.jsx";
const out = "C:/Personal/projects/FleetFlow/frontend/_err.txt";
try {
  const src = fs.readFileSync(file, "utf8");
  const { transformSync } = require("esbuild");
  transformSync(src, { loader: "jsx", format: "esm", sourcefile: file });
  fs.writeFileSync(out, "ESBUILD_OK");
} catch (e) {
  const msg = (e && e.errors ? JSON.stringify(e.errors, null, 2) : (e && e.message ? e.message : String(e)));
  fs.writeFileSync(out, msg);
}
