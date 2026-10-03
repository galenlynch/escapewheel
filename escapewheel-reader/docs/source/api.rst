API Reference
=============

.. currentmodule:: escapewheel_reader

Two tiers of names are public. The user tier is importable from ``escapewheel_reader``: open a
packet, then pass it to the functions in the later sections. The support tier is for another
Escapewheel package, and each of its names is imported from the module shown. A name this page
does not list is the reader's own and may change without notice.

Opening packets
---------------

.. autosummary::
   :toctree: generated

   open_packet
   Packet
   open_dataset
   Dataset
   Session

Reading tables
--------------

.. autosummary::
   :toctree: generated

   intervals
   units
   events
   spike_times
   distinct
   STORED

Clocks and seconds
------------------

.. autosummary::
   :toctree: generated

   attach_clocks
   on_clock
   seconds
   reference_clock
   origin
   align
   BOUND

Observation and rates
---------------------

.. autosummary::
   :toctree: generated

   unit_windows
   stream_windows
   clock_windows
   observed_ticks
   observed_seconds
   rate
   rate_of
   support_of

Spikes against events
---------------------

.. autosummary::
   :toctree: generated

   aligned_spikes
   assigned_spikes
   windows_disjoint

Runs and channels
-----------------

.. autosummary::
   :toctree: generated

   ambiguities
   preferred_run
   Ambiguity
   electrode_at
   kept_channels
   runs_without_channels
   ChannelsUndeclared

Discriminators
--------------

.. autosummary::
   :toctree: generated

   declared
   kinds
   resolved
   specialised
   unresolved
   Discriminator
   Unresolved

Array axes
----------

.. autosummary::
   :toctree: generated

   describe
   ArrayDescription
   Axis
   TickAxis
   NumericAxis
   IrregularAxis
   LabelledAxis
   Scaling

Manifest, resources and locations
---------------------------------

.. autosummary::
   :toctree: generated

   Manifest
   Resource
   RegistryBinding
   TableResource
   ArrayResource
   read_pool
   Location
   read_sources
   check_sources

Names in SQL
------------

.. autosummary::
   :toctree: generated

   sql_name
   quote

Errors
------

.. autosummary::
   :toctree: generated

   EscapewheelError
   PacketError
   ManifestError
   SourcesError
   RegistryUnavailable
   RegistryFault
   ResourceError
   ResourceNotFoundError
   ResourceUnreadableError
   UnsupportedCodecError
   UnresolvedSource
   NotDeclared
   Refused
   NoTimeOrigin
   NotAligned
   Unanchored
   AmbiguousRun
   StaleSupport
   UnresolvableChannelIndex
   ClockMismatch
   UnresolvableAxis
   AxisFault
   MultiSessionUnresolved
   PhysicalProfileError

Support tier
------------

For the validator, the writer and an adapter package. Every user-tier name is also importable from
the module that defines it.

.. autosummary::
   :toctree: generated

   protocols.PacketLike
   protocols.Memo
   clocks.ClockGraph
   clocks.anchors
   clocks.clock_columns
   clocks.clock_graph
   clocks.declared_bound
   clocks.extrapolation_error
   clocks.mapped
   optional.held
   optional.read_optional
   ordering.stored_order
   profile.PROFILE_ID
   profile.physical_profile
   profile.parquet_floor
   profile.zarr_floor_admits
   profile.zarr_floor_outside
   registries.acquire
   registries.declared_tables
   registries.gunzip_member
   uri.canonical
   uri.decode
   uri.encode
   uri.in_one_form
   uri.is_absolute
   uri.representable
   location.SOURCES_FILENAME
   location.SOURCES_VERSION
   manifest.MANIFEST_FILENAME
   manifest.MANIFESTS_DIRNAME
   resources.ZARR_METADATA_FILENAMES
   scripts.cli.main

``resource_ids`` is in the support tier whole: one constant for each core resource ID that code
names.

.. autosummary::
   :toctree: generated

   resource_ids

Modules
-------

A module's page carries its docstring; its public names are documented above.

.. autosummary::
   :toctree: generated

   access
   alignment
   axes
   channels
   clocks
   dataset
   discriminators
   observation
   packet
   runs
   manifest
   resources
   location
   errors
   sql
   protocols
   profile
   optional
   ordering
   registries
   uri
   scripts.cli
