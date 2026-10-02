# Rule-language conformance vectors

`vectors.json` is machine-readable evidence for the portable Tier 2 boundary in Part 11. Each
case names the selected profile, declared input relation shapes and rows, a query, and either the
expected parsed dependencies/result names, typed unordered result bag, or rejection class. A case
stating `expected_result_domains` also fixes each result column's SQL domain, in Part 11 §4's
spelling.

Run `probe.py` through the repository verifier. It executes a query as the reference validator
gives it to its engine. In addition to the explicit vectors, the probe
validates the maintained language descriptor, resolves every incorporated contract anchor, and
statically checks every shipped Tier 2 rule and binds its names to the declarations of its
registry and the core registry, failing when their count differs from the one `probe.py` states.
`conformance/registries/check.py` executes the same rules against typed empty relations.

These vectors test the incorporated contract; they do not define another language.
