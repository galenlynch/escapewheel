import * as zarr from "zarrita";
import FileSystemStore from "@zarrita/storage/fs";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const version = JSON.parse(readFileSync(join(here, "node_modules/zarrita/package.json"))).version;
console.log("zarrita", version, "node", process.version);
for (const set of ["arrays", "more", "writer_arrays", "endian"]) {
  const index = join(here, set, "expected.json");
  if (!existsSync(index)) continue;
  const expected = JSON.parse(readFileSync(index));
  // write.py records one sum for all its arrays and a per-config outcome.
  const sums = expected.configs
    ? Object.fromEntries(Object.keys(expected.configs).map((d) => [d, expected.sum]))
    : expected;
  for (const [name, sum] of Object.entries(sums)) {
    try {
      const array = await zarr.open(zarr.root(new FileSystemStore(join(here, set, name))), { kind: "array" });
      const chunk = await zarr.get(array);
      let total = 0;
      for (const v of chunk.data) total += Number(v);
      console.log(`${set}/${name}:`, total === sum ? "READ OK" : `WRONG ${total}`);
    } catch (error) {
      console.log(`${set}/${name}: FAIL`, String(error).slice(0, 150));
    }
  }
}
