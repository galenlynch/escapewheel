# Rule-language conformance vectors

`vectors.json` is machine-readable evidence for the portable Tier 2 boundary in Part 11. Each
case names the selected profile, declared input relation shapes and rows, a query, and either the
expected parsed dependencies/result names, typed unordered result bag, or rejection class.

Run `probe.py` through the repository verifier. In addition to the explicit vectors, the probe
validates the maintained language descriptor, resolves every incorporated contract anchor, and
statically checks and binds all 121 shipped Tier 2 rules against typed empty relations.

These vectors test the incorporated contract; they do not define another language.
