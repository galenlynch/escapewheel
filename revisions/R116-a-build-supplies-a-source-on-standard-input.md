# A Build Supplies a Source on Standard Input

| | |
|---|---|
| **Status** | **Accepted** 2026-09-14 |
| **Amends** | Part 03 §11.2 (the channel the supplied object crosses by), Part 05 §3.7 (what a build does with a command's standard input) |
| **Depends on** | R115 §3.1 (a build supplies exactly what an adapter declares, as one JSON object keyed by term), R115 §3.3 (rows cross by a protocol of a group), R115 §3.4 (a recipe carries a command as an argument list) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

This settles which channel carries what a build supplies a source, and nothing else about the
supply: the vocabulary of terms stays as Part 03 §11.2 declares it, the encoding stays JSON, and
what an adapter returns is untouched. Two actors are bound, a build and an adapter, and both are
bound only where the adapter runs out of process.

## 2. Motivation

### 2.1 The supplied object outgrows the argument list

Part 03 §11.2 has everything a build supplies cross as one JSON object keyed by the term, appended
to the command's argument list as its last element. An argument list has a size, and no profile can
raise it: Linux caps a single argument at **131,072 bytes** — 32 pages, `MAX_ARG_STRLEN` — and
Windows caps the whole command line at **32,767 characters**, so the portable ceiling is a quarter
of the smaller number a POSIX host enforces.

Measured on `ecephys_786867`, an AIND ecephys session of ten probes and **4,505 sorted units**, the
NWB adapter's object is **322,799 bytes**. A build delivering it fails before the adapter starts,
with `OSError: [Errno 7] Argument list too long` and no diagnosis of its own, because the failure is
in the process spawn rather than in anything either party wrote.

Two of the ten shipped adapters exceed the limit and the other eight are nowhere near it:

| adapter | bytes | terms it declares |
|---|---|---|
| `nwb` | **322,799** | `root`, `session_id`, `reference_clock`, `units` |
| `waveforms` | **322,355** | `root`, `session_id`, `units` |
| `lfp`, `sync` | 5,218 | `root`, `session_id`, `clocks` |
| `session` | 595 | `root`, `session_id`, `reference_clock` |
| `video` | 566 | `root`, `session_id`, `reference_clock` |
| `harp`, `openephys`, `sorter`, `tables` | 151 | `root`, `session_id` |

Both offenders exceed it for one reason: `units` is **322,193 bytes** over 4,505 records, so the
limit is reached at about **1,832 units** on Linux and about **450** on Windows. R115 §3.1 put the
NWB adapter's object at **721 bytes**, which is the same adapter measured against the conformance
fixture, where the sorting has no units and the term is an empty list.

### 2.2 Two terms grow with the session

Part 03 §11.2's vocabulary carries three collections. `units` is one record per sorted unit,
`first_samples` one per stream, and `clocks` one per clock the packet declares. The first grows
with what the session produced, and a session with twice the units doubles the object; the other
two grow with the rig, which is why `clocks` is 5,055 bytes over 11 rows and stays there.

So a cap on the term is a cap on the science, and the term is not what is wrong. What is wrong is a
channel whose size is fixed by the host and unrelated to anything a recipe declares.

### 2.3 Standard input carries nothing under any protocol

Rows take standard output under `stream-v0.1`, a directory under `files-v0.1` and a socket under
`flight-v0.1` (Part 03 §11.1), and a diagnosis takes standard error under all three (Part 05 §3.7).
Standard input carries nothing in any of them, has no size limit, and is the one channel every host
gives a child process before it runs.

It is also the one that does not publish what it carries. An argument list is readable by every
process on the machine through `/proc/<pid>/cmdline`, and a file written for the purpose outlives
the run in a workspace a failed build deliberately keeps.

## 3. Decision

### 3.1 A build writes the supplied object to standard input

A build **MUST** write what it supplies to the command's standard input, as the one JSON object
Part 03 §11.2 already defines — keyed by term, with the recipe's options under `options` — and
**MUST** close that stream when it has written it. A build **MUST NOT** pass the object as an
argument, and **MUST NOT** add any argument to the command the recipe carries.

An adapter **MUST** read its standard input to end of file and parse it as that object before it
writes any rows. A build supplies nothing else on that stream, so an adapter reads it once and needs
no framing of its own.

The terms a protocol requires rather than an adapter declaring them — `socket`, `delivery_root`,
`report_path` — travel inside the object as they do today.

### 3.2 A build writes without waiting for the command

A build **MUST** write and close standard input without waiting for the command to exit, and
**MUST** read what the command produces while it writes.

A pipe holds tens of kilobytes, and the object measured in §2.1 is two orders of magnitude past
that. A build that wrote it whole before reading rows would deadlock against an adapter whose first
rows fill the output pipe, and both would wait on the other for as long as the build allowed. This is Part 05
§3.7's existing obligation to capture standard output and standard error extended to the third
stream, and for the same reason. How a build does it is Part 07 §7's, being a technique that changes
with the implementation (R93 §4).

## 4. What this does not change

- **No term is capped, added or removed.** §2.1 measures one term past a host's limit and §2.2
  finds that term growing with every session, which together invite a bound on what a term may
  carry. The channel is what this replaces: Part 03 §11.2's vocabulary and the records each term
  takes are exactly as they were.

## 5. Consequence

**Two adapters become deliverable for a real session.** `nwb` and `waveforms` are the two the
argument list refused, and the objects that failed to cross — 322,799 and 322,355 bytes — cross in
one write. Every other adapter's object crosses as it did.

**A recipe is unchanged.** Its `command` never carried the object, so no recipe is edited and no
packet is rebuilt: this changes no table, column, reference, rule or vocabulary, and a packet built
before it is conforming under it.

**A reference implementation changes on both sides**, and by about as much as it sounds: the command
that serves an adapter reads the object from standard input rather than from its last argument, and
the build writes it on a thread of its own, beside the one that already drains standard error. The
seven scripts in `conformance/adapter-boundary/` take the object as `argv[1]`; they are the
measurement this boundary was designed against rather than an implementation of it, and they are
updated with the rest.

**Migration is nothing.** No adapter has been released independently of a build, so the only readers
of the argument form are in this repository.

**A person running an adapter by hand pipes the object**, where they used to quote it:
`escapewheel deliver nwb < supplied.json`. That is a better debugging story than the one it
replaces, since the object is a file they can read and re-send rather than a line they must escape.
