# R29 — Schema Provenance

| | |
|---|---|
| **Status** | **Accepted** 2026-08-28 |
| **Amends** | R2 §3 (registry document shape), §4 (column entry) |
| **Depends on** | R2 (schema registry format) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

Twenty-eight revisions have amended a frozen Part 02. The registry states the result and the
revisions state the reasoning, and nothing connects a particular column to the particular
decision that set it. Asking *why is `local_unit_label` a string* means grepping the
revisions for the column name and hoping the answer is phrased the way the search was.

That cost grows with every revision, and it is what makes people ask for a consolidated
specification. Consolidation as usually meant — a new frozen Part 02 restating the current
state — would answer *what* and destroy *why*, since `registry/build.py` derives structure by
parsing Part 02 and applying each revision in turn. Re-baselining the parser against a
consolidated document discards the chain it exists to preserve.

The provenance is not missing. It is in `build.py` as twenty-five block comments:

```python
# ---- R19 §3 : an electrode sits in more than one coordinate frame ----------------
# ---- R28 §2-4 : a unit sits on many electrodes, and somewhere --------------------
```

A comment is not data. Moving it into the registry gives a generated document that says both
what a table is and which decision made it so, which is what a consolidated specification was
wanted for.

## 2. New field: `since`

A table entry and a column entry MAY each carry a `since` field: the identifier of the
revision that introduced it, or that last changed it in a way a reader would want to trace.

```json
{
  "name": "local_unit_label",
  "type": "string",
  "presence": "nullable",
  "description": "Opaque source label; undefined base, not an offset.",
  "since": "R8 §2"
}
```

The value is free text naming a revision, optionally with a section — `R8`, `R8 §2`, `R3
§2.1`. It is **not** a reference to be resolved: a registry travels inside a packet (R2 §8)
and the revisions do not travel with it, so this is a citation for a reader, not a link a
validator follows.

A column with no `since` came from Part 02 unamended. That is a meaningful state and the reason
the field is optional rather than required: a registry built only from Part 02 carries none, and
saying so by omission is more honest than stamping every column with the base specification's
name.

### 2.1 `since` names one revision, not a history

A column amended twice carries the later revision. The earlier one is not lost — it is in
`revisions/`, which is the history — and a chain of them in the registry would be a changelog
in a document that packets embed.

## 3. Amendment to R2's meta-schema

R2 §3 defines `registry.schema.json` with `additionalProperties: false` at every level,
including `column`, so adding this field is a change to the registry *format* and not a
private extension. `$defs.table` and `$defs.column` each gain:

```json
"since": {"type": "string", "minLength": 1}
```

Neither is added to `required`.

**A packet written before this revision stays conforming**, and one written after stays
readable by a validator that predates it only if that validator ignores unknown fields —
which `additionalProperties: false` means it does not. So a registry carrying `since` requires
a validator built against this revision. That is the cost, and it is why this is a revision
rather than a convention.

## 4. What a renderer does with it

`registry/tables.md` is generated from the registry (`registry/render.py`). With `since`
present it cites the deciding revision beside each column, so the rendered document answers
both questions a consolidated specification would:

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `local_unit_label` | string | nullable | R8 §2 | Opaque source label; undefined base, not an offset. |

This revision does not specify the rendering. It specifies the field the rendering needs.

## 5. What this does not do

- **No new table and no rule.** `since` is documentation carried as data. There is nothing
  for SQL to check: a wrong citation is wrong in a way a query cannot see, exactly like a
  wrong `description`.
- **No consolidated specification.** `nwb_lake_poc_docs/` stays frozen and the revisions stay
  binding. This makes the generated view good enough that consolidating becomes a choice
  about release discipline rather than a remedy for unreadability — which is Phase 6's
  question, not this one's.
- **No provenance for rules.** A Tier 2 rule is authored in `rules.json` and already names
  its revision in the message text on the ones added since R11. Formalizing that is a
  separate and smaller question.
- **No machine-readable section anchors.** `R8 §2` is a string for a human. Making it
  resolvable would mean the revisions having stable anchors and the registry depending on
  documents it does not travel with.

## 6. Consequences for the registry

- `registry.schema.json` gains one optional property in two places.
- `build.py`'s twenty-five revision blocks each pass their own identifier, so the comment and
  the data cannot disagree.
- `check.py` SHOULD gain an invariant that every table and column introduced by a revision
  carries a `since` — not that every column does, since Part 02's own carry none.
- No table, column, type, presence, key, reference or rule changes. 32 tables, 268 columns.

## 7. Open

- **Whether Part 02's own columns should be stamped too**, with something like Part 02 rather than
  a revision. It would make the field uniformly present and lose the distinction between
  *unamended* and *unrecorded*.
- **Whether `since` should be structured** — `{"revision": "R8", "section": "2"}` rather than
  a string. Structure buys sorting and validation; a string is what a reader wants to see and
  costs nothing to write. The string is chosen on the grounds that nothing consumes it
  mechanically, and that stops being true if a tool ever links revisions.
