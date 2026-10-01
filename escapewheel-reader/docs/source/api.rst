API Reference
=============

.. currentmodule:: escapewheel_reader

Every name here is importable from ``escapewheel_reader``. Open a packet, then pass it to the
functions in the later sections; the :class:`Packet` methods that share their names delegate to
them.

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

Runs, channels, discriminators and arrays
-----------------------------------------

.. autosummary::
   :toctree: generated

   ambiguities
   preferred_run
   electrode_at
   kept_channels
   runs_without_channels
   declared
   kinds
   resolved
   specialised
   unresolved
   describe
   ArrayDescription

Manifest, resources and locations
---------------------------------

.. autosummary::
   :toctree: generated

   Manifest
   Resource
   RegistryBinding
   TableResource
   ArrayResource
   Location
   resolve_sources
   read_sources
   check_sources

Errors
------

.. autosummary::
   :toctree: generated

   EscapewheelError
   PacketError
   ManifestError
   SourcesError
   RegistryUnavailable
   ResourceError
   ResourceNotFoundError
   ResourceUnreadableError
   UnsupportedCodecError
   Refused
   NoTimeOrigin
   NotAligned
   AmbiguousRun
   StaleSupport
   ChannelsUndeclared
   UnresolvableChannelIndex
   UnresolvedSource
   ClockMismatch
   UnresolvableAxis
   MultiSessionUnresolved

Modules
-------

Each module's page lists everything it holds, including what is not exported above.

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
   profile
   descriptor
   ordering
   registries
   dictionaries
   sql
   uri
