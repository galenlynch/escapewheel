"""Source adapters for one institution's formats.

Core ships adapters for standards -- SpikeInterface, Open Ephys, Harp, NWB -- because many
institutions read them. What serves one institution lives here: `session.json` and the rest of
AIND's metadata schema, the behaviour videos and their headerless CSV, and the dialect columns an
AIND pipeline writes into an otherwise ordinary NWB.

The boundary, not the directory, is what this package is for
------------------------------------------------------------

It sits in the monorepo beside the writer and is built as though it already lived elsewhere: it
depends on `escapewheel-writer` the way that package depends on the validator, registers its kinds
through the `escapewheel.sources` entry-point group rather than by being listed in
`escapewheel_writer.sources.ADAPTERS`, and imports nothing of the writer that a registered adapter
released separately could not import. Moving it out is then a packaging change rather than a
rewrite.

That discipline costs something a recipe author sees. A build refuses a kind it neither ships nor
is told how to reach, so a recipe naming one of these declares `in_process = true` or a
`[source.delivery]` command (Part 05 §3.9) -- where naming a built-in kind declares nothing.
"""

__all__: list[str] = []
