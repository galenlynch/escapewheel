API Reference
=============

.. currentmodule:: escapewheel_writer

Every name in the sections before ``Modules`` is importable from ``escapewheel_writer``.

Building a packet
-----------------

.. autosummary::
   :toctree: generated

   build
   Recipe
   PacketWriter
   CommitRefused
   verify

Clocks
------

.. autosummary::
   :toctree: generated

   Clock
   OffGrid
   NonFinite

Errors
------

Every exception the package raises on purpose derives from ``WriterError``. The enumerations hold
the codes an error or a reported problem carries.

.. autosummary::
   :toctree: generated

   WriterError
   RecipeError
   RecipeUnreadable
   RecipeUnsound
   UnknownSourceKind
   SourcesNotOrdered
   TermUnfilled
   MaterializerNotFound
   NotesUnderStrict
   RecipeFault
   ReplacementRefused
   AmendmentRefused
   ExtensionNotFound
   DeclarationUnreadable
   SourceDefect
   UnsupportedEncoding
   DeliveryFailed
   SourceFault
   PayloadRefused
   PayloadProblem
   PayloadFault
   UsageError
   UsageFault
   UndeclaredResource
   UnknownCompensation
   CompensationsInvalid
   FixedOffsetZone
   NaiveTimestamp
   CarriedNotAnInteger
   OutOfRange
   TickOverflow
   Collided
   PacketOccupied
   NotCommitted
   PromotionRecordUnreadable

Notes
-----

What an adapter or a build worked around, as text carrying a code.

.. autosummary::
   :toctree: generated

   Note
   NoteCode

Modules
-------

Each module's page lists what it holds beyond the names above.

.. autosummary::
   :toctree: generated

   recipe
   session
   writer
   sources
   keys
   clock
   arrow
   encoding
   arrays
   opaque
   materialize
   amending
   replacing
   compare
   declaration
   delivery
   extensions
   scaffold
   verify
   prune
   errors
   notes

Source adapters
---------------

.. autosummary::
   :toctree: generated

   sources.nwb
   sources.sorter
   sources.sync
   sources.waveforms
   sources.lfp
   sources.openephys
   sources.harp
   sources.store
   sources.zarr_compat
   sources.compensations
   sources.values
