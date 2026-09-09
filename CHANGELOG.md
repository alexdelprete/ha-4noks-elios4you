# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-09-09

Stable release consolidating the three 1.4.0 betas — everything below is new since v1.3.1.
Full credit to @RickyReds: the protocol reverse engineering, the initial implementation
(#182, reported in #181), the discovery-protocol find, and four rounds of real-hardware beta
testing including a genuine blackout that validated the statistics behaviour.

### ✨ Features

- **Smart RC wireless accessory support.** The `DEVHA<n>` rows in `@dat` (one per accessory
  paired to the Red Cap module) were parsed as plain `name;value` pairs and discarded. Each
  accessory now gets five sensors — Power (W), Energy (Wh, `total_increasing`), Signal (dBm),
  Name, ZigBee Device ID — plus two binary sensors: Online (`connectivity`) and Relay.
- **New `binary_sensor` platform** for the two genuinely binary accessory states. Relay is
  read-only: `@rel <n>` accessory addressing was tested on real hardware and is silently
  ignored by the device.
- **Dynamic accessory entities.** Entities are created the moment their data first appears
  (accessory paired after HA starts, or an offline accessory coming online) and removed when
  an accessory is un-paired — no integration reload in either direction. Verified on
  hardware: creation and cleanup both within one poll.
- **Per-slot generation, neutral naming.** Any number of accessories is supported without
  code changes ("Accessory N" — the Red Cap pairs plugs, switches, relays, power reducers
  and energy meters). The ZigBee Device ID diagnostic sensor exists so users can report
  values for types other than the Smart Plug (`81`/`0x0051`, the only one confirmed).
- **Host auto-discovery.** The device answers an undocumented discovery protocol on UDP 5002
  (`Elios4you` → `HELLO <serial>`); the add-integration form broadcasts a probe and
  pre-fills the host field. Non-exclusive (never disturbs a running integration),
  best-effort, verified on two networks and two firmware generations. Requires the HA
  process to have LAN broadcast access (host networking).
- **ZigBee radio diagnostics**: Red Cap channel and PAN ID as disabled-by-default sensors,
  for diagnosing accessory interference.

### 🐛 Bug Fixes

- **Offline accessories no longer report zeros** for power, energy and RSSI: a zero energy
  reading is read by the statistics engine as a meter reset, inflating the Energy dashboard
  on every offline/online cycle. Last-known values persist while offline; only Online and
  Relay reflect the offline row. Survived a provoked counter reset and a real 35-minute
  blackout with statistics tracking exactly.
- Signal sensor icon is `mdi:zigbee` (ZigBee link, not WiFi).

### 🔧 Changed

- **Minimum Home Assistant version raised to 2026.8.0** (was 2026.3.0). HACS will not offer
  this update on older installations.
- Replaced the deprecated `device_registry.async_get_device` API (removal in HA 2027.8) with
  `async_get_or_create`'s return value.
- New `CONTRIBUTING.md` centered on the devcontainer; `requirements-dev.txt` dropped —
  `pyproject.toml` is the single dependency source. CI tests against HA 2026.9.

### 📚 Documentation

- Known Limitations and a Smart RC Troubleshooting section built from real-hardware
  findings: accessory counters resume from a periodic internal save after power loss
  (statistics adjust downward, undetectable); re-pairing zeroes the counter; Relay is not a
  reachability indicator (watch Online); accessory relays cannot be switched locally;
  entities are slot-keyed, so a replacement accessory inherits entities, history and stored
  preferences; the 4-noks app's Save-settings leaves the accessory relay open indefinitely;
  the per-socket operating mode can silently revert to Automatic; a stuck relay state is
  fixable by factory reset; the app's Smart RC screen does not auto-refresh.

### ⚠️ Breaking Changes

**None for installations upgrading from v1.3.1** — every accessory entity is new, and all
pre-existing entity `unique_id`s are unchanged. Note the raised HA minimum (2026.8.0).

---

## [1.4.0-beta.3] - 2026-09-08

Incremental over v1.4.0-beta.2, driven by @RickyReds' four-day stability soak and his
discovery of the device's UDP discovery protocol.

### ✨ Features

- **Host auto-discovery in the config flow.** The device answers an undocumented discovery
  protocol on UDP port 5002 (`Elios4you` → `HELLO <serial>`), found by capturing the official
  app's traffic. The add-integration form now probes the network and pre-fills the host field
  with the first responding device. Best-effort: unlike telnet, the UDP endpoint is
  non-exclusive, so probing never disturbs a running integration, and manual entry always
  works.
- **ZigBee radio diagnostics**: Red Cap channel and PAN ID exposed as disabled-by-default
  diagnostic sensors — the data needed to diagnose accessory interference (the most common
  Smart RC complaint) was read on every poll but never surfaced.

### 📚 Documentation

- ⚠️ Two warnings in Troubleshooting from real-hardware findings: **saving accessory settings
  in the 4-noks app opens the relay and leaves it open indefinitely** (the load stays dead
  until manually re-enabled), and **the per-socket operating mode can silently revert to
  Automatic** with no way to detect it over the local protocol.

---

## [1.4.0-beta.2] - 2026-09-04

Incremental over v1.4.0-beta.1, driven by @RickyReds' beta report on real hardware.

### ✨ Features

- **Stale-entity cleanup**: un-pairing an accessory now removes its entities automatically.
  The API prunes the data keys of any `DEVHA<n>` slot that stops appearing in `@dat`, and the
  platforms remove the matching registry entries — slot-level, so a merely *offline* accessory
  (which keeps emitting its row) is never touched. Re-pairing recreates the entities cleanly.

### 🔧 Changed

- **Accessory Relay is definitively read-only.** The `@rel <n> <state>` accessory-addressing
  hypothesis was tested on real hardware and falsified: the device accepts a non-zero index
  and silently ignores it. A switch entity will not be added unless a working command is ever
  captured from the official app's traffic.

### 📚 Documentation

- README Known Limitations now documents three findings from real-hardware testing:
  accessories may lose part of their internal Wh counter on power loss (statistics can adjust
  downward — understated, never inflated); Relay is not a reachability indicator (watch
  Online); accessory relays cannot be switched via the local protocol.
- Release notes now include manual installation steps alongside HACS.

---

## [1.4.0-beta.1] - 2026-09-04

First pre-release since v1.3.1. Everything below is new relative to that release.
Full credit to @RickyReds for the protocol reverse engineering, the initial implementation,
and the production testing behind the accessory support (reported in #181, implemented in #182).

### ✨ Features

- **Smart RC wireless accessories are now exposed as sensors.** The `DEVHA<n>` rows returned by
  `@dat` carry ten fields per accessory paired to the Red Cap radio module (online, relay, power,
  energy, RSSI, ZigBee device ID, name), but the parser treated every row as a plain
  `name;value` pair and kept only the first field. Each accessory now gets five sensors (Power,
  Energy, Signal, Name, Device ID) plus two binary sensors (Online, Relay).
- **New `binary_sensor` platform.** Accessory Online (device class `connectivity`) and Relay are
  genuinely binary states — the relay is a real physical contact in the accessory — so they are
  binary sensors rather than 0/1 numeric sensors. Relay stays read-only until the `@rel <n>`
  accessory-addressing hypothesis is confirmed on real hardware; if it holds, it becomes a switch.
- **Accessory entities are created dynamically at runtime.** A coordinator listener adds entities
  the moment their data first appears: an accessory paired after Home Assistant starts, or an
  accessory that was offline at the first poll coming online, gets its entities on the next poll —
  no integration reload needed.
- **Sensors are generated per discovered slot**, not from hardcoded `devha0`/`devha1` blocks, so
  a third or fourth paired accessory is exposed without a code change. The slot number is
  injected into the entity name via `translation_placeholders`, keeping translations at seven
  strings per language.
- **Neutral naming — "Accessory N", not "Smart Plug N".** The Red Cap pairs Smart Plug RC, Smart
  Switch RC, Smart Relay RC, Power Reducer RC and Energy Meter RC. The ZigBee HA 1.2 Device ID is
  exposed as a diagnostic sensor (disabled by default) so users can report the value for
  accessory types other than the Smart Plug — `81`/`0x0051` is the only one confirmed so far.

### 🐛 Bug Fixes

- **Offline accessories no longer report zeros for power, energy and RSSI.** `devha<n>_energy` is
  `TOTAL_INCREASING`: a `0` reading is read by the statistics engine as a meter reset, so on
  every offline/online cycle the whole counter was added to the Energy dashboard again, inflating
  statistics. RSSI `0` misleads in the other direction — 0 dBm reads as a very strong signal.
  When field `[5]` (online) is `0`, those three keys are now omitted from the parsed row; since
  `Elios4YouAPI.data` is merged into and never rebuilt, the last known values simply persist.
  Only `_online` and `_relay` take the offline row's values.
- **Signal sensor uses `mdi:zigbee`** instead of `mdi:wifi-strength-2`: the accessory link is
  ZigBee, not WiFi.

### 🔧 Changed

- **Minimum Home Assistant version raised to 2026.8.0** (was 2026.3.0). HACS will not offer this
  update on older HA installations.
- **Replaced the deprecated `device_registry.async_get_device` API** (warning since HA 2026.9,
  removal in HA 2027.8): the post-create device lookup now uses `async_get_or_create`'s return
  value directly.
- **New `CONTRIBUTING.md`** documenting the devcontainer as the supported development path;
  `requirements-dev.txt` was dropped — `pyproject.toml` is the single source of truth for
  development dependencies. Tests now run against HA 2026.9.0 in CI
  (`pytest-homeassistant-custom-component` 0.13.363).

### ⚠️ Breaking Changes

**None for installations upgrading from v1.3.1** — every accessory entity is new in this
release, and all pre-existing entity `unique_id`s are unchanged. (If you were running the
`main` branch between releases: accessory Online and Relay moved from the sensor platform to
the new binary_sensor platform and their display names changed from "Smart Plug N …" to
"Accessory N …" — remove the orphaned sensor entities from the entity registry.)

⚠️ **One behaviour worth knowing:** if an accessory is *already offline* when the integration
first polls, its power, energy and signal entities are not created until it comes back online —
because those keys have never existed. This is deliberate: an entity reporting 0 W for an
accessory nobody has ever heard from would be a fabricated measurement. Online and Relay are
always created.

---

## [1.3.1] - 2026-05-31

🐛 **Patch Release** — fixes a single options-flow bug reported during v1.3.0 testing.

### 🐛 Bug Fixes

- **Recovery Script can now be cleared via the Options flow.** Previously, clearing the
  Recovery Script field and submitting had no effect — reopening the Options form showed the
  old value still attached. Root cause was `vol.Optional(CONF_RECOVERY_SCRIPT, default=...)`:
  voluptuous substituted the saved value back in whenever the EntitySelector arrived empty,
  so the cleared submission carried the stale value all the way to storage. Switched to
  `description={"suggested_value": ...}`, which pre-fills the form for display without
  resurrecting the value on an empty submission.

### ✅ Tests

- Regression test added that exercises the actual voluptuous schema (the bug lived in schema
  validation, which direct `async_step_init` calls bypass).

### ⚠️ Breaking Changes

**None** — pure bug fix. Any existing recovery script that's still wanted continues to work
unchanged.

**Full Release Notes:** [docs/releases/v1.3.1.md](docs/releases/v1.3.1.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.3.0...v1.3.1>

---

## [1.3.0] - 2026-05-31

🎉 **Official Stable Release** — ConnectionManager refactor, adaptive backoff, and connection
diagnostics that resolve the recurring "device deafness" symptom.

This release promotes the `1.3.0-beta.1` work to stable after multi-day validation on a live
device: **17 silent timeouts were auto-recovered over an 8-hour window with 0 command failures,
0 offline events, and ~99.96% connection reuse**, and the manual "kick the device off WiFi"
workaround went unused for days. See the beta entry below for the full architecture detail.

### 📊 Diagnostics (changed since beta.1)

- **Four** connection diagnostic sensors are now **enabled by default** (was two). Added
  `Connection Silent Timeouts` and `Connection Last Error` to the defaults:
  - `Connection State` and `Connection Consecutive Failures` show link health, but
    auto-recovery keeps both at their healthy values during transient "deaf device" events.
  - `Connection Silent Timeouts` is the **only** sensor that surfaces those auto-recovered
    events — without it, a device still going deaf under the hood is invisible.
  - `Connection Last Error` is empty when healthy but is the most useful field for diagnosing
    a problem or filing a bug report.
- The remaining eight diagnostic sensors stay opt-in.

### 🏗️ Architecture

- **Extracted `ConnectionManager`** (`connection_manager.py`) — the connection lifecycle is now
  an explicit state machine (`DISCONNECTED → CONNECTING → READY → BACKOFF`, terminal `CLOSED`)
  that owns the single TCP/telnet session and serialises every command. `api.py` is now a thin
  parser/orchestrator on top of it; public API unchanged.

### 🚀 Reliability (device-deafness mitigations)

- **Reuse window raised to 90 s** (was 25 s) — one TCP session persists across the poll cadence
  instead of churning a fresh socket every minute.
- **Retries dropped from 3 to 1** per command — caps the worst-case connect-storm.
- **TCP RST on error close** (`transport.abort()`) — a failed command drops the socket with RST
  so the device frees its slot immediately instead of waiting out CLOSE_WAIT.
- **Bounded `wait_closed()`** — a misbehaving device can no longer hang the integration on close.
- **Exponential backoff** (5 s → 60 s) after 3 consecutive failures — the manager refuses new
  connections while in backoff, giving the device room to recover.

### 🔧 Logging

- **Structured `(ConnMgr.*)` log prefix** for every state transition, connect attempt, retry,
  close, and backoff event. Scope it via
  `custom_components.4noks_elios4you.connection_manager: debug`.

### 🧹 Code Quality

- Dropped all `# type: ignore` comments; `DataUpdateCoordinator[bool]` and
  `CoordinatorEntity[Elios4YouCoordinator]` are now properly parameterised.
- Removed the unused `check_port()` and `as_diagnostics()` helpers.
- Test coverage at 99% overall (211 tests).

### 📚 Documentation

- README updated with the new architecture, `(ConnMgr.*)` log format, and the four
  default-enabled diagnostic sensors.

### ⚠️ Breaking Changes

**None** — `api.py`'s public surface is unchanged. Existing config entries, sensors, the relay
switch, and automations keep working without modification.

**Full Release Notes:** [docs/releases/v1.3.0.md](docs/releases/v1.3.0.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.2.0...v1.3.0>

---

## [1.3.0-beta.1] - 2026-05-27

🧪 **Beta Release** — ConnectionManager refactor + adaptive backoff to address recurring "device deafness".

Please test this beta on your real device for 2–3 days before it is promoted to stable. The
two new diagnostic sensors enabled by default (`Connection State` and
`Connection Consecutive Failures`) make it easy to confirm the integration is healthy at a glance.

**Full Release Notes:** [docs/releases/v1.3.0-beta.1.md](docs/releases/v1.3.0-beta.1.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.2.0...v1.3.0-beta.1>

### 🏗️ Architecture

- **Extracted `ConnectionManager`** (`connection_manager.py`) — the connection lifecycle is now
  an explicit state machine (`DISCONNECTED → CONNECTING → READY → BACKOFF`, terminal `CLOSED`)
  that owns the single TCP/telnet session and serialises every command. `api.py` is now a
  thin parser/orchestrator on top of it; public API unchanged.

### 🚀 Reliability (device-deafness mitigations)

- **Reuse window raised to 90 s** (was 25 s) — the same TCP session now persists across the
  default 60 s poll cadence instead of churning a fresh socket every minute.
- **Retries dropped from 3 to 1** per command — caps the worst-case connect-storm on a flaky
  cycle at ~6 SYNs instead of ~12.
- **TCP RST on error close** (`transport.abort()`) — when a command fails the socket is dropped
  with RST so the device frees its slot immediately rather than waiting out CLOSE_WAIT.
- **Bounded `wait_closed()`** — a misbehaving device can no longer hang the integration on close.
- **Exponential backoff** (5 s → 60 s) after 3 consecutive failures — while in backoff the
  manager refuses to even attempt a new connection, giving the device room to recover.

### 📊 Diagnostics

- **12 new diagnostic sensors** under the device's Diagnostic section: `Connection State`,
  `Connection Consecutive Failures`, `Connection Backoff Remaining`, `Connection Silent Timeouts`,
  `Connection Forced Aborts`, `Connection Reuse Hits`, `Connection Connects Succeeded`,
  `Connection Connect Failures`, `Connection Commands Sent / Failed / Retried`, and
  `Connection Last Error`. `Connection State` and `Connection Consecutive Failures` are enabled
  by default; the rest are opt-in.
- **Downloadable diagnostics** now include a `connection_manager` section with the full
  metrics snapshot.

### 🔧 Logging

- **Structured `(ConnMgr.*)` log prefix** for every state transition, connect attempt, retry,
  close, and backoff event. Target it directly via
  `custom_components.4noks_elios4you.connection_manager: debug` to see manager-only logs.

### 🧹 Code Quality

- **Type-checker cleanup**: dropped all `# type: ignore` comments. `DataUpdateCoordinator[bool]`
  and `CoordinatorEntity[Elios4YouCoordinator]` are now properly parameterised, and the
  Unicode telnetlib3 variants are `cast()` at the assignment site.
- Dropped the no-longer-used `check_port()` method and the unused `as_diagnostics()` helper.

### 📚 Documentation

- README updated with the new architecture, log format, and diagnostic sensors.
- All pre-existing pymarkdown MD032 violations (CLAUDE.md, CHANGELOG.md, README.md, and the
  full docs/releases/ history) are fixed — Lint CI is green again.

### ⚠️ Breaking Changes

**None** — `api.py`'s public surface (`async_get_data`, `telnet_set_relay`, `close`,
`data`, `name`, `host`) is unchanged. Existing config entries, sensors, and automations
continue to work without modification.

---

## [1.2.0] - 2026-01-04

🔧 **Stability & Test Infrastructure Release** - Improved recovery notifications and comprehensive test coverage

### 🐛 Bug Fixes

- **Recovery notifications:** Changed from repair issues to persistent notifications for better reliability
  - Notifications now survive Home Assistant restarts
  - Users must explicitly dismiss to acknowledge recovery
  - More visible and actionable

### ✅ Test Infrastructure

- **98% code coverage** with 221 passing tests
- **New test files:**
  - `test_repairs.py` - Recovery notification tests
  - `test_device_trigger.py` - Device trigger tests
- **Improved fixtures:**
  - Added `hass.loop` and `hass.state` to `mock_hass` fixture
  - Resolved missing mock attributes causing test failures
- **CI improvements:**
  - Created `requirements-dev.txt` for separated dev dependencies
  - Added JSON linting to lint workflow
  - Improved test workflow with proper dependency installation

### 📚 Documentation

- **CLAUDE.md:** Added mandatory pre-commit directive, RRC clarifications, download badge format

### ⚠️ Breaking Changes

**None** - Full backward compatibility maintained.

**Full Release Notes:** [docs/releases/v1.2.0.md](docs/releases/v1.2.0.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.1.1...v1.2.0>

---

## [1.1.1] - 2026-01-02

### 🐛 Bug Fixes

- **Repairs flow handler:** Fixed empty recovery notification issue by adding `ConfirmRepairFlow` handler

### 🔧 Code Quality

- **Exception handling:** Refactored to use specific exceptions instead of catch-all handlers (aligned with
  ha-sinapsi-alfa patterns)
- **Code patterns:** Aligned with ha-sinapsi-alfa coding standards (list comprehensions, simplified conditionals)
- **Pre-commit:** Added pre-commit configuration for automated code quality checks
- **Test imports:** Replaced importlib workaround with symlink approach (consistent with ty type checker)
- **Tests:** Updated tests to match refactored exception handling behavior

### 📚 Documentation

- **CLAUDE.md:** Added local test instructions with symlink workaround
- **CLAUDE.md:** Added directive to never modify production code to make tests pass

---

## [1.1.0] - 2026-01-02

🎉 **Official Stable Release** - Recovery script, device triggers, enhanced notifications, and UI improvements

This release includes all improvements from the v1.1.0 beta cycle, bringing automated recovery scripts, device
automation triggers, enhanced recovery notifications with detailed timing, and options flow UI improvements.

### ✨ New Features

#### Recovery Script (Optional)

Configure an optional script that automatically executes when the device stops responding. This enables automated
recovery actions like restarting your WiFi router or power-cycling network equipment.

**Configuration:** In Options flow, select a script entity to run when failures exceed the configured threshold.

**Available variables for script:**

- `device_name` - The configured device name
- `host` - The device IP address
- `port` - The device TCP port

**Example use case:** Configure a script that restarts your WiFi access point when the Elios4you device becomes
unreachable, enabling automatic network recovery.

#### Device Triggers for Automations

Added 3 device triggers to enable Home Assistant automations based on device connection events:

| Trigger | Event | Description |
|---------|-------|-------------|
| `device_unreachable` | Network/TCP connection failed | Fires when device cannot be reached on the network |
| `device_not_responding` | Connected but not responding | Fires when device is reachable but telnet commands fail |
| `device_recovered` | Device responding again | Fires when device recovers after a failure |

**Usage:** In HA Automations, go to "Device" trigger and select your Elios4You device to see available triggers.

#### Enhanced Recovery Notifications

Improved repair notifications with detailed timing information:

- **Failure started:** Time when the issue began (locale-aware format)
- **Script executed:** Time when recovery script ran (if configured)
- **Recovery time:** Time when device recovered
- **Total downtime:** Compact format (e.g., "5m 23s", "1h 15m")
- **Persistent notifications:** Survive HA restarts, require user acknowledgment

**Example notification:**

```text
Title: My Elios4You has recovered

Your Elios4You device is now responding again.

Failure started: 14:32:15
Script executed: 14:32:18
Recovery time: 14:37:38
Total downtime: 5m 23s

The recovery script script.restart_wifi was executed.

Please dismiss this notification to acknowledge.
```

#### Options Flow UI Improvements

Rearranged the options flow dialog for better UX:

| Order | Field | Change |
|-------|-------|--------|
| 1 | Recovery script | Moved up (right after variables description) |
| 2 | Enable repair notifications | Unchanged position |
| 3 | Failures before notification | Changed from slider to input box |
| 4 | Polling Period | Moved to bottom |

#### Min-Max Validation in Field Labels

All numeric input fields now display their validation ranges:

- TCP port: `(1-65535)`
- Polling Period: `(30-600)`
- Failures threshold: `(1-10)`

### 🌐 Translations

All 10 languages fully updated with new features:

- English, Italian, German, Spanish, French, Portuguese, Estonian, Finnish, Norwegian, Swedish

### 📦 Files Changed

- `custom_components/4noks_elios4you/device_trigger.py` (NEW) - Device trigger implementation
- `custom_components/4noks_elios4you/coordinator.py` - Recovery script execution, trigger firing, downtime tracking
- `custom_components/4noks_elios4you/repairs.py` - Enhanced notification function
- `custom_components/4noks_elios4you/__init__.py` - Register device triggers platform
- `custom_components/4noks_elios4you/config_flow.py` - Recovery script selector, UI improvements, NumberSelector
- All 10 translation files - Complete updates with all new features and min-max values

### ⚠️ Breaking Changes

**None** - Full backward compatibility maintained.

**Full Release Notes:** [docs/releases/v1.1.0.md](docs/releases/v1.1.0.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.0.0...v1.1.0>

---

## [1.1.0-beta.2] - 2026-01-02

🔧 **Beta Release** - Options flow UI improvements

### ✨ Improvements

#### Options Flow UI Rearrangement

Rearranged the options flow dialog for better UX:

| Order | Field | Change |
|-------|-------|--------|
| 1 | Recovery script | Moved up (right after variables description) |
| 2 | Enable repair notifications | Unchanged position |
| 3 | Failures before notification | Changed from slider to input box |
| 4 | Polling Period | Moved to bottom |

**Technical changes:**

- Changed `failures_threshold` from `vol.Clamp` slider to `NumberSelector` with `mode=BOX`
- Changed `scan_interval` to `NumberSelector` with `unit_of_measurement="seconds"`
- Reordered schema fields for logical grouping

### 📦 Files Changed

- `custom_components/4noks_elios4you/config_flow.py` - Reordered options schema, added NumberSelector imports

### ⚠️ Breaking Changes

**None** - Full backward compatibility maintained.

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.1.0-beta.1...v1.1.0-beta.2>

---

## [1.1.0-beta.1] - 2026-01-02

🔧 **Beta Release** - Device triggers and enhanced recovery notifications

### ✨ New Features

#### Device Triggers for Automations

Added 3 device triggers to enable Home Assistant automations based on device connection events:

| Trigger | Event | Description |
|---------|-------|-------------|
| `device_unreachable` | Network/TCP connection failed | Fires when device cannot be reached on the network |
| `device_not_responding` | Connected but not responding | Fires when device is reachable but telnet commands fail |
| `device_recovered` | Device responding again | Fires when device recovers after a failure |

**Usage:** In HA Automations, go to "Device" trigger and select your Elios4You device to see available triggers.

#### Enhanced Recovery Notifications

Improved repair notifications with detailed timing information:

- **Failure started:** Time when the issue began (locale-aware format)
- **Script executed:** Time when recovery script ran (if configured)
- **Recovery time:** Time when device recovered
- **Total downtime:** Compact format (e.g., "5m 23s", "1h 15m")
- **Persistent notifications:** Survive HA restarts, require user acknowledgment

**Example notification (with recovery script):**

```text
Title: My Elios4You has recovered

Your Elios4You device is now responding again.

Failure started: 14:32:15
Script executed: 14:32:18
Recovery time: 14:37:38
Total downtime: 5m 23s

The recovery script script.restart_wifi was executed.

Please dismiss this notification to acknowledge.
```

### 📦 Files Changed

- `custom_components/4noks_elios4you/device_trigger.py` (NEW) - Device trigger implementation
- `custom_components/4noks_elios4you/coordinator.py` - Trigger firing and downtime tracking
- `custom_components/4noks_elios4you/repairs.py` - Enhanced notification function
- `custom_components/4noks_elios4you/__init__.py` - Register device triggers platform
- `custom_components/4noks_elios4you/config_flow.py` - ConfigFlow VERSION bump to 3
- All 10 translation files - Added trigger and notification strings

### 🌐 Translations

All 10 languages updated with new strings:

- English, Italian, German, Spanish, French, Portuguese, Estonian, Finnish, Norwegian, Swedish

### ⚠️ Breaking Changes

**None** - Full backward compatibility maintained.

**Full Release Notes:** [docs/releases/v1.1.0-beta.1.md](docs/releases/v1.1.0-beta.1.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.0.0...v1.1.0-beta.1>

---

## [1.0.0] - 2025-12-31

🎉 **First Stable v1.0.0 Release** - Production-ready integration

This milestone release represents a mature, battle-tested integration that has undergone extensive development and
testing, achieving **Home Assistant Quality Scale Gold tier compliance**.

### 🚀 Journey from v0.2.0 to v1.0.0

| Version | Milestone |
|---------|-----------|
| v0.3.0-beta.1 | Connection pooling fix for device "deaf" issue |
| v0.4.0-beta.1 | Full async telnetlib3 migration |
| v0.4.0-beta.2 | telnetlib3 API optimization |
| v0.4.0-beta.3 | Comprehensive test suite (98% coverage) |
| **v1.0.0** | **Production-ready stable release** |

### ✨ Key Features

- **Full Async I/O** - telnetlib3 for non-blocking telnet operations
- **Connection Pooling** - 25-second reuse window prevents device socket exhaustion
- **98% Test Coverage** - 188 tests across all components
- **HA Quality Scale Platinum** - Full compliance with all tiers including strict typing
- **Config/Options/Reconfigure Flows** - Complete configuration management
- **Repair Notifications** - Connection issues surfaced in HA repairs system
- **Diagnostics Support** - Downloadable diagnostics for troubleshooting
- **10 Language Translations** - EN, DE, ES, ET, FI, FR, IT, NB, PT, SV
- **Type Checking with ty** - Astral's Rust-based type checker

### 📝 Documentation

- **Known Limitations Section** - Documents single device per instance
- **Troubleshooting Section** - Debug logging, repair notifications, issue reporting
- **Updated Features** - Repair notifications and diagnostics documented

### ⚠️ Breaking Changes

**None** - Migration from any previous version is seamless.

### 📦 Requirements

- Home Assistant 2025.10.0 or newer
- Python 3.13 or newer

**Full Release Notes:** [docs/releases/v1.0.0.md](docs/releases/v1.0.0.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.2.0...v1.0.0>

---

## [0.4.0-beta.3] - 2025-12-29

🔧 **Beta Release** - Test infrastructure, bug fixes, and ty type checker

### ✅ Test Infrastructure

- **Comprehensive Test Suite** - 188 tests passing with 98% code coverage
- Test files: `conftest.py`, `test_api.py`, `test_config_flow.py`, `test_coordinator.py`, `test_init.py`,
  `test_sensor.py`, `test_switch.py`
- Established testing patterns for numeric module prefix workaround

### 🐛 Bug Fixes

- **Fixed `async_remove_config_entry_device`** - Device identifiers check was incorrect (set of tuples, not strings)

### 🔧 CI/CD Enhancements

- **New Workflows:** `test.yml`, `validate.yml`, `release.yml`
- **Type Checker Migration** - Migrated from mypy to [ty](https://github.com/astral-sh/ty) (Astral's Rust-based type
  checker)
- Symlink workaround for numeric package name in type checking

### 📝 Documentation

- Updated README with CI badges and ty documentation
- Added comprehensive ty instructions in CLAUDE.md

**Full Release Notes:** [docs/releases/v0.4.0-beta.3.md](docs/releases/v0.4.0-beta.3.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.4.0-beta.2...v0.4.0-beta.3>

---

## [0.4.0-beta.2] - 2025-12-29

🔧 **Beta Release** - telnetlib3 API optimization

### 🐛 Bug Fixes

- **Fixed telnetlib3 API Usage** - Updated to use strings instead of bytes
  - telnetlib3 works with strings internally (handles encoding)
  - Removed unnecessary `.encode()` and `.decode()` calls
  - Aligned with library's documented usage patterns

### 📝 Documentation

- Added comprehensive v0.4.0-beta.1 release documentation

**Full Release Notes:** [docs/releases/v0.4.0-beta.2.md](docs/releases/v0.4.0-beta.2.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.4.0-beta.1...v0.4.0-beta.2>

---

## [0.4.0-beta.1] - 2025-12-29

🔧 **Beta Release** - Migrate to telnetlib3 async client

### ♻️ Major Architecture Changes

- **Migrated to telnetlib3 Async Client** ⭐ MOST IMPORTANT - Replaced bundled synchronous telnetlib with telnetlib3 for
  fully async I/O operations. This prevents blocking the Home Assistant event loop during telnet operations.

### 🐛 Problem Solved

**Before (Sync Blocking):**

- `read_until()` could block the event loop for up to 5 seconds per command
- Other integrations, automations, and UI updates would freeze during telnet I/O
- Home Assistant responsiveness degraded during polling cycles

**After (Async Non-Blocking):**

- All telnet I/O operations yield control to the event loop
- Other tasks run while waiting for device responses
- Home Assistant remains responsive during polling

### ✨ New Methods

- **`_async_read_until()`** - Custom async read-until-separator helper for stream-based reading
- **`_async_send_command()`** - Fully async command execution (replaces sync `telnet_get_data()`)
- **`async _ensure_connected()`** - Async connection pooling with timeout
- **`async _safe_close()`** - Async graceful connection cleanup
- **`async close()`** - Public async close method

### 📦 Files Changed

- `custom_components/4noks_elios4you/api.py` - Major rewrite (~80% of file)
  - Removed `E4Utelnet` class (no longer needed)
  - Added async telnetlib3 client (reader/writer streams)
  - All I/O operations now fully async
- `custom_components/4noks_elios4you/__init__.py` - Updated to `await` async `close()` method
- `custom_components/4noks_elios4you/const.py` - Version bump to 0.4.0-beta.1
- `custom_components/4noks_elios4you/manifest.json` - Version bump to 0.4.0-beta.1
- `custom_components/4noks_elios4you/telnetlib/__init__.py` - **Deleted** (bundled sync telnetlib no longer needed)

### 🔄 Migration Summary

| Component | Before (Sync) | After (Async) |
|-----------|---------------|---------------|
| Import | `from .telnetlib import Telnet` | `import telnetlib3` |
| Client | `E4Utelnet()` class | `reader, writer` tuple |
| Connect | `E4Uclient.open()` | `await telnetlib3.open_connection()` |
| Write | `E4Uclient.write()` | `writer.write(); await writer.drain()` |
| Read | `E4Uclient.read_until()` | `await _async_read_until()` |
| Close | `E4Uclient.close()` | `await writer.wait_closed()` |

### ✅ Preserved Features

All existing functionality is preserved:

- ✅ Connection pooling (25-second reuse window)
- ✅ Command retry logic (3 retries, 300ms delay)
- ✅ Race condition prevention via asyncio.Lock
- ✅ Silent timeout detection
- ✅ Same exception handling (TelnetConnectionError, TelnetCommandError)

### ✅ Code Quality

- 100% Ruff compliance maintained
- Net reduction of 680 lines (+194 / -874)
- Removed bundled telnetlib (672 lines)

### ⚠️ Breaking Changes

**None**. This is an internal refactor with full backward compatibility.

**Full Release Notes:** [docs/releases/v0.4.0-beta.1.md](docs/releases/v0.4.0-beta.1.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.3.0-beta.1...v0.4.0-beta.1>

---

## [0.3.0-beta.1] - 2025-12-29

🔧 **Beta Release** - Fix device "deaf" issue with connection pooling

### 🐛 Critical Bug Fixes

- **Fixed Device "Deaf" Issue** ⭐ MOST IMPORTANT - Implemented connection pooling to prevent socket exhaustion that
  caused device to become unresponsive 50-60 times/day
- **Fixed Socket Exhaustion** - Eliminated double socket usage (check_port + connection) per poll cycle
- **Fixed TIME_WAIT Accumulation** - Connection reuse prevents socket backlog on embedded device
- **Fixed Silent Timeouts** - Added detection for incomplete responses in `telnet_get_data()`
- **Fixed Global Timeout Mutation** - Changed `socket.setdefaulttimeout()` to socket-specific `settimeout()`
- **Fixed Race Conditions** - Added `asyncio.Lock` to serialize telnet operations between polling and switch commands

### ✨ New Features

- **Connection Pooling** - Reuse existing telnet connections for up to 25 seconds
- **Graceful Connection Close** - New `_safe_close()` method with proper buffer draining and TCP shutdown
- **Connection Health Checks** - New `_is_connection_valid()` method validates connection before reuse

### ♻️ Architecture Improvements

- **Removed Redundant Update Listener** - Aligned with ha-sinapsi-alfa by removing manual
  `async_on_unload(add_update_listener())` - `OptionsFlowWithReload` handles this automatically
- **New Connection Management Methods**:
  - `_is_connection_valid()` - Check if existing connection can be reused
  - `_safe_close()` - Graceful close with buffer drain
  - `_ensure_connected()` - Open connection only if needed
- **Refactored `async_get_data()`** - Uses connection lock and pooling, no longer calls `check_port()` separately
- **Refactored `telnet_set_relay()`** - Uses same connection lock to prevent race conditions with polling

### ✅ Code Quality

- 100% Ruff compliance maintained
- Fixed SIM105 linting errors by using `contextlib.suppress()` instead of try-except-pass patterns
- Import optimization with `contextlib` module

### 📝 Technical Details

**Root Cause Analysis:**
The device became "deaf" due to socket exhaustion on the embedded Elios4You device. Each poll cycle opened 2 sockets
(check_port + connection), creating ~120 sockets/hour with 30-second polling. Combined with 2-minute TIME_WAIT
persistence, this overwhelmed the device's limited socket backlog.

**Solution:**

- Eliminated redundant `check_port()` call before each connection
- Implemented 25-second connection reuse window
- Added asyncio.Lock to serialize all telnet operations
- Added graceful socket shutdown with buffer draining
- Added silent timeout detection for incomplete responses

**Expected Results:**
| Metric | Before | After |
|--------|--------|-------|
| Sockets per poll | 2 | 0-1 (reuse) |
| TIME_WAIT accumulation | 120/hour | ~2/hour |
| Race condition risk | High | None (locked) |
| Device "deaf" events | 50-60/day | ~0 |

### 📦 Files Changed

- `custom_components/4noks_elios4you/api.py` - Connection pooling implementation
- `custom_components/4noks_elios4you/__init__.py` - Removed redundant update listener
- `custom_components/4noks_elios4you/const.py` - Version bump
- `custom_components/4noks_elios4you/manifest.json` - Version bump
- `.gitignore` - Added build/ directory

### ⚠️ Breaking Changes

**None**. This is a bug fix release with full backward compatibility.

**Full Release Notes:** [docs/releases/v0.3.0-beta.1.md](docs/releases/v0.3.0-beta.1.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.2.0...v0.3.0-beta.1>

---

## [0.2.0] - 2025-10-15

🎉 **Official Stable Release** - Comprehensive code quality improvements and bug fixes

This is the official stable release that includes ALL improvements from the beta cycle (beta.1, beta.2, beta.3) plus
dependency updates for Home Assistant 2025.10.x compatibility.

### 🐛 Critical Bug Fixes

- **Fixed Sensor Availability** ⭐ MOST IMPORTANT - Sensors now properly show "unavailable" when device is offline
  instead of displaying stale data
- **Fixed Integration Unload KeyError** - Simplified unload logic to prevent crashes during integration removal
- **Fixed Missing Await** - Corrected async/await pattern in reload function
- **Fixed API Close Method** - Added missing `close()` method to properly cleanup telnet connections
- **Removed Pymodbus Dependency** - Eliminated incorrect import of unused pymodbus library

### ♻️ Architecture Improvements

- **New `helpers.py` Module** - Standardized logging functions across entire codebase
  - Contextual logging: `log_debug()`, `log_info()`, `log_warning()`, `log_error()`
  - Consistent format: `(function_name) [context]: message`
  - Support for structured context data via kwargs
  - Added `host_valid()` utility function

- **Core Module Refactoring (`__init__.py`)**:
  - Simplified `RuntimeData` - removed redundant `update_listener` field
  - Converted `async_update_device_registry()` to sync with `@callback` decorator
  - Updated `async_reload_entry()` to use `async_schedule_reload()` (non-blocking pattern)
  - Refactored `async_unload_entry()` with walrus operator and cleaner error handling
  - Added `async_migrate_entry()` infrastructure for future config migrations
  - Simplified update listener to one-line pattern

- **Logging Standardization** - Updated ALL Python files:
  - `__init__.py` - 5 logger calls updated
  - `api.py` - ~30 logger calls updated
  - `config_flow.py` - 5 logger calls updated
  - `coordinator.py` - 4 logger calls updated
  - `switch.py` - 4 logger calls updated
  - `sensor.py` - 2 logger calls updated
  - Removed all f-strings from logging for better performance

- **Config Flow Improvements**:
  - Host validation moved to shared `helpers.host_valid()` function
  - Removed code duplication
  - Consistent error logging with context

### ✨ Code Quality Improvements

- Added custom exception classes: `TelnetConnectionError` and `TelnetCommandError`
- Enhanced error handling with proper exception propagation and context
- Added comprehensive type hints throughout codebase
- Improved logging patterns (structured logging with % formatting)
- Achieved 100% ruff compliance
- Code formatting and cleanup
- 8 Python files refactored (7 existing + 1 new)

### 📦 Dependencies & Compatibility

- **Updated for Home Assistant 2025.10.x:**
  - Home Assistant requirement: `2025.10.0+` (was `2025.1.0`)
  - Python requirement: `3.13+` (was `3.11`)
  - Development dependencies: `homeassistant==2025.10.2`, `pip>=21.0,<25.3`
  - Telnet library: `telnetlib3>=2.0.4` (unchanged)
  - Code quality: `ruff==0.14.0`

- **CI/CD Updates:**
  - GitHub Actions lint workflow now uses Python 3.13
  - Ensures compatibility with latest Home Assistant core

### 🎯 ABB Power-One v4.1.5 Alignment

Successfully adopted the following patterns:

- Contextual helper logging functions
- Custom exception classes with context
- `@callback` decorator for sync operations
- Non-blocking reload with `async_schedule_reload()`
- Clean error propagation in unload
- Simplified RuntimeData structure
- Migration infrastructure
- DRY principle with shared utilities

### ⚠️ Breaking Changes

**None** for existing users. This is a code quality and bug fix release with full backward compatibility.

**For new installations:**

- Requires Home Assistant 2025.10.0 or newer
- Requires Python 3.13 or newer

### 📝 Beta Testing Cycle

This stable release is the result of thorough beta testing:

- v0.2.0-beta.1 (2025-10-12) - Critical bug fixes and code quality
- v0.2.0-beta.2 (2025-10-12) - Hotfix for unload error
- v0.2.0-beta.3 (2025-10-13) - Architecture alignment
- v0.2.0 (2025-10-15) - Official stable with dependency updates

**Full Release Notes:** [docs/releases/v0.2.0.md](docs/releases/v0.2.0.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.1.0...v0.2.0>

---

## [0.2.0-beta.3] - 2025-10-13

🏗️ **Architecture Alignment Release** - Major internal refactoring for code quality

### ♻️ Architecture Improvements

- **New `helpers.py` Module** - Standardized logging functions across entire codebase
  - Contextual logging: `log_debug()`, `log_info()`, `log_warning()`, `log_error()`
  - Consistent format: `(function_name) [context]: message`
  - Support for structured context data via kwargs
  - Added `host_valid()` utility function

- **Core Module Refactoring (`__init__.py`)**:
  - Simplified `RuntimeData` - removed redundant `update_listener` field
  - Converted `async_update_device_registry()` to sync with `@callback` decorator
  - Updated `async_reload_entry()` to use `async_schedule_reload()` (non-blocking pattern)
  - Refactored `async_unload_entry()` with walrus operator and cleaner error handling
  - Added `async_migrate_entry()` infrastructure for future config migrations
  - Simplified update listener to one-line pattern

- **Logging Standardization** - Updated ALL Python files:
  - `__init__.py` - 5 logger calls updated
  - `api.py` - ~30 logger calls updated
  - `config_flow.py` - 5 logger calls updated
  - `coordinator.py` - 4 logger calls updated
  - `switch.py` - 4 logger calls updated
  - `sensor.py` - 2 logger calls updated
  - Removed all f-strings from logging for better performance

- **Config Flow Improvements**:
  - Host validation moved to shared `helpers.host_valid()` function
  - Removed code duplication
  - Consistent error logging with context
  - Alphabetically sorted exception imports
  - Added type ignore comment for ConfigFlow class

- **Code Formatting Improvements**:
  - Improved readability with line breaks in long logging calls (api.py)
  - Enhanced type hints with return type annotations
  - Consistent style according to ruff standards

### ✅ Code Quality

- 100% Ruff compliance maintained
- Zero new linting warnings
- Comprehensive type hints throughout
- Consistent logging format across entire codebase
- Improved code readability with better formatting
- 8 Python files refactored (7 existing + 1 new)

### 🎯 ABB Power-One v4.1.5 Alignment

Successfully adopted the following patterns:

- Contextual helper logging functions
- `@callback` decorator for sync operations
- Non-blocking reload with `async_schedule_reload()`
- Clean error propagation in unload
- Simplified RuntimeData structure
- Migration infrastructure
- DRY principle with shared utilities

### 📝 Files Changed

- `helpers.py` (NEW) - Standardized utility functions
- `__init__.py` - Core integration lifecycle refactoring
- `api.py`, `config_flow.py`, `coordinator.py`, `switch.py`, `sensor.py` - Logging standardization
- `manifest.json` - Version bump to v0.2.0-beta.3

### ⚠️ Breaking Changes

**None**. This is an internal refactoring with no user-facing changes.

**All improvements from v0.2.0-beta.1 and v0.2.0-beta.2 are included in this release.**

**Full Release Notes:** [docs/releases/v0.2.0-beta.3.md](docs/releases/v0.2.0-beta.3.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.2.0-beta.2...v0.2.0-beta.3>

---

## [0.2.0-beta.2] - 2025-10-12

🔧 **Hotfix Release** - Fixes integration unload error from v0.2.0-beta.1

### 🐛 Bug Fix

- **Fixed Integration Unload Error** - Added missing `close()` method to `Elios4YouAPI` class to prevent error during
  integration unload/shutdown

### 📝 Technical Details

- Added `close()` method to `Elios4YouAPI` class that properly delegates to internal telnet client
- Error message was: `'Elios4YouAPI' object has no attribute 'close'`
- Now cleanly closes telnet connection during integration unload

**Files Changed:**

- `custom_components/4noks_elios4you/api.py` - Added close() method

**All improvements from v0.2.0-beta.1 are included in this release.**

**Full Release Notes:** [docs/releases/v0.2.0-beta.2.md](docs/releases/v0.2.0-beta.2.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.2.0-beta.1...v0.2.0-beta.2>

---

## [0.2.0-beta.1] - 2025-10-12

⚠️ **This is a BETA release** - Please test thoroughly before using in production

### 🐛 Critical Bug Fixes

- **Fixed Sensor Availability** ⭐ MOST IMPORTANT - Sensors now properly show "unavailable" when device is offline
  instead of displaying stale data
- **Fixed Integration Unload KeyError** - Simplified unload logic to prevent potential crashes
- **Fixed Missing Await** - Corrected async/await pattern in reload function
- **Removed Pymodbus Dependency** - Eliminated incorrect import of unused pymodbus library

### ✨ Code Quality Improvements

- Added custom exception classes: `TelnetConnectionError` and `TelnetCommandError`
- Enhanced error handling with proper exception propagation
- Added comprehensive type hints throughout codebase
- Improved logging patterns (structured logging with % formatting)
- Achieved 100% ruff compliance
- Code formatting and cleanup

### ♻️ Modernization

- Aligned with ABB Power-One PVI SunSpec integration v4.1.5 patterns
- Updated to Home Assistant 2025.3.0+ best practices
- Simplified integration lifecycle management

### 📦 Dependencies

- telnetlib3 >= 2.0.4
- ruff 0.14.0 (dev)
- Python >= 3.13 target

### 📝 Documentation

- Created comprehensive release notes
- Added CLAUDE.md documenting AI-assisted development process
- Improved inline code documentation

**Full Release Notes:** [docs/releases/v0.2.0-beta.1.md](docs/releases/v0.2.0-beta.1.md)

**Full Changelog:** <https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.1.0...v0.2.0-beta.1>

---

## [0.1.0] - 2024-02-20

Initial release of the 4-noks Elios4you integration.

### Features

- Installation/Configuration through Config Flow UI
- Sensor entities for all data provided by the device
- Switch entity to control the device internal relay
- Configuration options: Name, hostname, tcp port, polling period
- Runtime reconfiguration support (except device name)

### Technical Details

- Based on ABB Power-One PVI SunSpec integration architecture
- Uses telnet protocol (port 5001) instead of Modbus
- Reverse-engineered protocol based on work by Davide Vertuani
- Supports multiple Elios4you devices
- Local polling integration (no cloud dependency)

---

[Unreleased]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.3.1...HEAD
[1.3.1]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.2.0...v1.3.0
[1.3.0-beta.1]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.2.0...v1.3.0-beta.1
[1.2.0]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.0.0...v1.1.0
[1.1.0-beta.2]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.1.0-beta.1...v1.1.0-beta.2
[1.1.0-beta.1]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.0.0...v1.1.0-beta.1
[1.0.0]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.4.0-beta.3...v1.0.0
[0.4.0-beta.3]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.4.0-beta.2...v0.4.0-beta.3
[0.4.0-beta.2]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.4.0-beta.1...v0.4.0-beta.2
[0.4.0-beta.1]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.3.0-beta.1...v0.4.0-beta.1
[0.3.0-beta.1]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.2.0...v0.3.0-beta.1
[0.2.0]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.1.0...v0.2.0
[0.2.0-beta.3]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.2.0-beta.2...v0.2.0-beta.3
[0.2.0-beta.2]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.2.0-beta.1...v0.2.0-beta.2
[0.2.0-beta.1]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.1.0...v0.2.0-beta.1
[0.1.0]: https://github.com/alexdelprete/ha-4noks-elios4you/releases/tag/v0.1.0
