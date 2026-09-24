# Drafts

A draft is candidate normative text for a problem whose scope and intended direction have already
been settled. Exploratory work belongs in `../proposals/`; start a draft from
`../templates/draft.md`.

A draft has no number. It gets one only after acceptance is authorized, taken from the end of the
accepted range, so the numbered space reads in the order revisions were **applied**
rather than the order they were written. Nothing outside this directory may cite a draft by number,
because it has none, and a draft does not change the authoritative generated v0.2 specification.

Why: an `R<N>` is permanent once accepted: it identifies the accepted record, its clause-ledger
entries, and its evidence manifest. Git preserves the earlier stages. Assigning a number at drafting
time would force application order to match drafting order or require those permanent references to
be renumbered.

A draft cites another draft by its file name in backticks. At acceptance those citations become
`R<N> §<x>`, which is a step in the acceptance sequence in `../CONTRIBUTING.md`.

## Application order

Dependencies run downward, so a draft may depend on the ones above it and on nothing below.

| order | draft | words | appraisal | placement |
|---:|---|---:|---|---|
| 1 | [A Packet Passes Only When Its Manifest, Core, and Every Bound Extension Pass](a-packet-passes-only-when-its-manifest-core-and-every-bound-extension-pass.md) | 2804 | Ready for acceptance; appraised 2026-09-23 against `0b82c8a`, the anchor bootstrap after `d9b6686`. Depends on R130 §§3.6 and 3.9 and R131 §3.3; no other open work. Material findings: extension parity is scoped to checks a core resource receives by kind or declaration, so the session-inventory check does not extend; the gate binds every published manifest version, including the writer's `verify`; Part 04 §9 cites the gate rather than restating it. The re-run probe reports only the validator fixture's `int64` `task.trials.session_id`, and all 29 corpus packets, 565 writer tests, and 66 AIND tests behave as before. No accepted clause is superseded. | Part 05 section 9.5 added; Part 00 §4.1, Part 04 §§9–10, Part 05 §§5.3, 5.4, 9.2, 10, and 14.5, and Part 09 §5.4 in place |
