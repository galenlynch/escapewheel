# R85 — A Device Declares Which Port It Attached To

| | |
|---|---|
| **Status** | **Accepted** 2026-09-06 |
| **Amends** | Part 02 (`core.devices`), R67 §2.1 (attachment is the reference, not the name) |
| **Depends on** | R66 (a device declares what version it was), R67 (a device names what it was attached to) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

`core.devices` holds every element of an acquisition chain, and R67 §2 gave it `parent_device_id`
so a probe can say which headstage it sat in. Measured on the two packaged sessions,
**`ecephys_776259`** and **`ecephys_786867`**, it holds 20 and 21 rows.

## 1. Motivation

### 1.1 A device's name is the only place its position is written

Seven of those twenty rows carry a serial number: the probes, named `46101`, `50198` and so on.
The other thirteen carry none, and are named for where they sit — `basestation.slot3`,
`connect_board.slot4`, `headstage.slot3.port4`. Those are the rows a probe's
`parent_device_id` points at.

R67 §2.1 forbids reading them: *"a consumer MUST NOT infer attachment from a name;
`headstage.slot3.port2` is a name this specification does not constrain, and the reference is the
statement."* The reference does say which device a probe hung off. It does not say **which port
of it**, and that fact exists in the packet only inside the string a consumer has been told not to
parse.

### 1.2 The serials that would name these devices are zero

Open Ephys records the chain in `settings.xml`, and its serial fields are empty of information.
Across the ten `NP_PROBE` elements of one session, `bs_serial_number`, `bsc_serial_number` and
`headstage_serial_number` each hold **one distinct value, `0`**. Only `probe_serial_number` is
real: **7 distinct values across 10 elements**, the repeats being the shanks of a quad-base.

What the same element does carry is `slot`, `port` and `dock` — the coordinates of each link in
the chain. So the position is available from the source, and the identity is not.

### 1.3 A positional name cannot be dropped, and cannot be trusted

The two failures meet. Because the writer numbers a device by its name (R53 §2.5), and because
thirteen rows have no serial and repeat their part number — every headstage is an `NPM_HS_30` —
the position is what keeps them apart. Strip it and they collapse into one device.

Keeping it is not safe either. **11 names appear in both packets and none of them carries a
serial**, and two disagree about what occupied them: `headstage.slot3.port4` and
`headstage.slot4.port2` are `hardware_version` **1.8** in one session and **0.1** in the other. A
name that identifies a slot rather than an object is a name two sessions can reuse for different
hardware, which is what makes `core.devices` session-scoped and what a consumer merging packets
would get wrong.

## 2. Decision

### 2.1 A device declares the port it attached to

`core.devices` gains **`parent_port`**, `string`, nullable: which port, dock or slot of
`parent_device_id` this device was attached to. Open, because the coordinate a link is named by
differs along the chain — a probe attaches to a dock, a headstage to a port, a card to a slot —
and no vocabulary this specification could close covers a rig it has not seen.

A writer that reads the attachment SHOULD record the port beside it. A writer that knows the
parent and not the port leaves it null, which R66 §1.4's discipline requires: an unfilled field is
not evidence of need, and an invented one is worse.

### 2.2 A device's name stays unique, and position is how

`device_name` is unchanged, and MAY still encode position where nothing else distinguishes a
device. §1.3 measures why: it is the only unique name thirteen of these rows have, and R53 §2.5
numbers a device by it.

**A `*_name` MUST be unique within its packet, and an adapter is what guarantees it.** R53 §2.5
assigns a number per distinct name, so two devices sharing a name become **one device** — one row
where the session had two, with no error and no rule to catch it. That is R67 §3's defect
mirrored: R67 found four rows claiming four probes where the session had one, and a name collision
produces the reverse.

It cannot be checked. A writer cannot distinguish two things wrongly sharing a name from one thing
seen twice, and the second is what R67 depends on — four streams naming one serial correctly
collapse to one device. The obligation therefore falls on the adapter composing the name, and this
revision states it rather than pretending a rule could.

That is the whole reason a basestation is called `basestation.slot3` and not by its model. Three
carriers of one type share a part number, so naming them for what they are would merge them;
naming them for where they sit keeps them apart. The position is load-bearing in the name, which
is why §2.1 adds a column rather than cleaning the name up.

A consumer **MUST NOT** read a port out of a name, which is R67 §2.1 restated with somewhere else
to look. Where `parent_port` is null the attachment's port is **unrecorded**, and a consumer MUST
report it as such rather than parse the name for it.

### 2.3 A port establishes nothing about identity

`parent_port` is not unique, alone or beside `parent_device_id`, and **no rule asserts that it
is**. A consumer MUST NOT read two rows sharing a parent and a port as one device.

Both packets already show why. `slot 7 port 1 dock 1` appears **four times in each session** — the
four shanks of a quad-base, one physical probe on one dock, which R67 §3 collapses to a single
`core.devices` row and four `core.probes` rows. One attachment point, four logical probes, and
the port cannot tell them apart because it is not about them.

Nothing rules out the general case either. A Neuropixels headstage carries two docks, so two
probes may sit on one; two of these sessions' probes already use `dock 2`, and only the accident
of how these rigs were loaded keeps a headstage from holding a pair. Devices sharing a bus are the
same shape one level up. A port says where something was plugged in, and re-introducing identity
through it would leave the packet no better than the name it replaces.

## 3. What this does not change

- **No connection entity.** The attachment stays two columns on the child, as R67 §2 made it. A
  table of connections would model a rig, and authoring a packet is already the constraint that
  keeps `core.devices` as shallow as it is.
- **`core.devices` stays session-scoped.** It reaches `core.sessions` through its declared
  references, and §1.3's two hardware versions are why that is right rather than incidental.
- **No packet becomes invalid.** The column is nullable and both measured packets pass with it
  unset until they are rebuilt.
- **R67's reference is untouched.** `parent_device_id` still states attachment; this states one
  more fact about it.

## 4. Consequence

One nullable column on a table holding 20 and 21 rows. The Open Ephys adapter already parses the
element that carries `slot`, `port` and `dock` — R67 §3 has it reading `custom_probe_name` from
the same attributes — so filling it costs a lookup rather than a read.

No rule is added. A port cannot be checked against anything: the packet holds no model of a rig to
contradict, which is the same reason R67 added no rule for the chain beyond well-foundedness.

## 5. Open

- **Whether a serial-bearing device should be recognised across packets.** A probe is the same
  object in two sessions and `probe_serial_number` says so, while `device_id` is packet-scoped and
  `device_name` is a serial only sometimes. Unifying on the serial is a cross-packet question this
  revision does not reach, and it is the same question a multi-packet reader has to answer for
  every assigned identifier.
- **Whether a device should say which kind of name it has.** Seven rows are named by serial and
  thirteen by position, and nothing distinguishes them — a consumer cannot tell whether
  `device_name` is an identity or an address. `core.devices.serial_number` already holds the
  identity where one exists, so the narrow fix is to say that cross-packet correspondence for a
  device runs through the serial and not the name, which R53 §2.3.1 assumes of every table alike.
  The general fix is a registry declaration of which column carries a thing's identity outside its
  packet — the same question R86 §5 asks of `*_name` — and neither is drafted here because no
  consumer has yet had to tell the two kinds apart.
- **Whether the port belongs on the parent instead.** A basestation has four ports and could
  enumerate what filled them, which is how a rig is usually drawn. It is rejected here because it
  makes the parent's row depend on how many children a packet happens to hold, where a column on
  the child is one fact per row.
