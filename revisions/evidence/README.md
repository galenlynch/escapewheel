# Revision change and evidence manifests

Each accepted revision that declares `Decision clauses` has one `R<N>.json` here. The manifest is
the mechanical closure record connecting each clause to:

- its authoritative Markdown section or JSON declaration;
- generated projections that must remain synchronized;
- an exact conformance fixture, pytest node ID, or named mechanical check;
- affected implementation paths, or a reason implementations are unchanged; and
- affected human documentation, or a reason it is unchanged.

The manifest does not make an implementation or test authoritative. Its `owners` are the
authoritative destinations; the other fields show how incorporation was propagated and checked.
List more than one owner only when one Decision clause changes multiple distinct declarations. Do
not list a generated rendering or implementation as a second owner of the same fact.

Copy `../templates/change-evidence.json`, name it for the accepted revision, and replace every
placeholder. `../evidence.py` rejects missing and extra clauses, missing paths, unresolved JSON
Pointers or Markdown sections, corpus findings not collected by `fixtures/corpus.py`, pytest node
IDs not collected by the named package, and check identifiers absent from the named `verify.py`
stage.

Historical revisions without explicit `Decision clauses` remain covered by `applied.toml`; they
predate this manifest format and are not silently assigned evidence they never recorded.
