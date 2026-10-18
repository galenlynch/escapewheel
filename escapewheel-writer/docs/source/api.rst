API Reference
=============

.. currentmodule:: escapewheel_writer

Two tiers of names are public. The user tier is importable from ``escapewheel_writer``: it builds a
packet from a recipe and maintains one already published. The adapter tier is for a source adapter
in another distribution, and each of its names is imported from ``escapewheel_writer.adapter``. A
name this page does not list is the writer's own and may change without notice.

Building a packet
-----------------

.. autosummary::
   :toctree: generated

   import_packet
   Recipe
   build
   PacketWriter
   materializers
   materialize_spike_events

Maintaining a packet
--------------------

.. autosummary::
   :toctree: generated

   verify
   prune

Notes
-----

What an adapter or a build worked around, as text carrying a code.

.. autosummary::
   :toctree: generated

   Note
   NoteCode

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
   AmendmentFault
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
   OffGrid
   NonFinite
   CarriedNotAnInteger
   OutOfRange
   TickOverflow
   Collided
   CommitRefused
   PacketOccupied
   NotCommitted
   PromotionRecordUnreadable

The adapter contract
--------------------

What a build holds an adapter to (Part 05 §3.4): every adapter is a ``SourceAdapter``, and each
other protocol is one capability a build tests for. ``escapewheel_writer.adapter`` also carries
``Note``, ``NoteCode``, ``SourceDefect``, ``SourceFault`` and ``UnsupportedEncoding`` from the user
tier, so an adapter imports from one module.

.. autosummary::
   :toctree: generated

   adapter.SourceAdapter
   adapter.Streams
   adapter.StagesArrays
   adapter.ReferencesArrays
   adapter.ReferencesMedia
   adapter.ReferencesResources
   adapter.StagesPayloads
   adapter.DeclaresCompensations
   adapter.WithholdsAnchors
   adapter.Located

What an adapter returns
-----------------------

.. autosummary::
   :toctree: generated

   adapter.StagedArray
   adapter.ExternalArray
   adapter.ExternalMedia
   adapter.ExternalResource
   adapter.Payload
   adapter.coded
   adapter.codes
   adapter.Compensation
   adapter.Compensates
   adapter.COMPENSATION_GROUP

Reading a source
----------------

.. autosummary::
   :toctree: generated

   adapter.Clock
   adapter.epoch_from
   adapter.zone_of
   adapter.HARP_TICK_RATE_HZ
   adapter.TICK_MIN
   adapter.TICK_MAX
   adapter.SourceStore
   adapter.source_root
   adapter.store_uri
   adapter.sex
   adapter.utc_offset
   adapter.clean
   adapter.ABSENT
   adapter.NWBSource
   adapter.SortedStream
   adapter.STREAM_FOLDER
   adapter.ANALYZERS

Registering and delivering
--------------------------

.. autosummary::
   :toctree: generated

   adapter.SOURCE_GROUP
   adapter.discovered
   adapter.ADAPTERS
   adapter.STREAM
   adapter.FILES
   adapter.FLIGHT
   adapter.PROTOCOLS
   adapter.document_of
   adapter.shape_problems
   adapter.TERMS
   adapter.serve
   adapter.build_table
   adapter.write_zarr

Modules
-------

.. autosummary::
   :toctree: generated

   adapter
