# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [1.0.0] - 2025-12-31

🎉 **First Stable v1.0.0 Release** - Production-ready integration

This milestone release represents a mature, battle-tested integration that has undergone extensive development and testing, achieving **Home Assistant Quality Scale Gold tier compliance**.

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

**Full Changelog:** https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.2.0...v1.0.0

---

## [0.4.0-beta.3] - 2025-12-29

🔧 **Beta Release** - Test infrastructure, bug fixes, and ty type checker

### ✅ Test Infrastructure

- **Comprehensive Test Suite** - 188 tests passing with 98% code coverage
- Test files: `conftest.py`, `test_api.py`, `test_config_flow.py`, `test_coordinator.py`, `test_init.py`, `test_sensor.py`, `test_switch.py`
- Established testing patterns for numeric module prefix workaround

### 🐛 Bug Fixes

- **Fixed `async_remove_config_entry_device`** - Device identifiers check was incorrect (set of tuples, not strings)

### 🔧 CI/CD Enhancements

- **New Workflows:** `test.yml`, `validate.yml`, `release.yml`
- **Type Checker Migration** - Migrated from mypy to [ty](https://github.com/astral-sh/ty) (Astral's Rust-based type checker)
- Symlink workaround for numeric package name in type checking

### 📝 Documentation

- Updated README with CI badges and ty documentation
- Added comprehensive ty instructions in CLAUDE.md

**Full Release Notes:** [docs/releases/v0.4.0-beta.3.md](docs/releases/v0.4.0-beta.3.md)

**Full Changelog:** https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.4.0-beta.2...v0.4.0-beta.3

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

**Full Changelog:** https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.4.0-beta.1...v0.4.0-beta.2

---

## [0.4.0-beta.1] - 2025-12-29

🔧 **Beta Release** - Migrate to telnetlib3 async client

### ♻️ Major Architecture Changes

- **Migrated to telnetlib3 Async Client** ⭐ MOST IMPORTANT - Replaced bundled synchronous telnetlib with telnetlib3 for fully async I/O operations. This prevents blocking the Home Assistant event loop during telnet operations.

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

**Full Changelog:** https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.3.0-beta.1...v0.4.0-beta.1

---

## [0.3.0-beta.1] - 2025-12-29

🔧 **Beta Release** - Fix device "deaf" issue with connection pooling

### 🐛 Critical Bug Fixes

- **Fixed Device "Deaf" Issue** ⭐ MOST IMPORTANT - Implemented connection pooling to prevent socket exhaustion that caused device to become unresponsive 50-60 times/day
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

- **Removed Redundant Update Listener** - Aligned with ha-sinapsi-alfa by removing manual `async_on_unload(add_update_listener())` - `OptionsFlowWithReload` handles this automatically
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
The device became "deaf" due to socket exhaustion on the embedded Elios4You device. Each poll cycle opened 2 sockets (check_port + connection), creating ~120 sockets/hour with 30-second polling. Combined with 2-minute TIME_WAIT persistence, this overwhelmed the device's limited socket backlog.

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

**Full Changelog:** https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.2.0...v0.3.0-beta.1

---

## [0.2.0] - 2025-10-15

🎉 **Official Stable Release** - Comprehensive code quality improvements and bug fixes

This is the official stable release that includes ALL improvements from the beta cycle (beta.1, beta.2, beta.3) plus dependency updates for Home Assistant 2025.10.x compatibility.

### 🐛 Critical Bug Fixes

- **Fixed Sensor Availability** ⭐ MOST IMPORTANT - Sensors now properly show "unavailable" when device is offline instead of displaying stale data
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

**Full Changelog:** https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.1.0...v0.2.0

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

**Full Changelog:** https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.2.0-beta.2...v0.2.0-beta.3

---

## [0.2.0-beta.2] - 2025-10-12

🔧 **Hotfix Release** - Fixes integration unload error from v0.2.0-beta.1

### 🐛 Bug Fix

- **Fixed Integration Unload Error** - Added missing `close()` method to `Elios4YouAPI` class to prevent error during integration unload/shutdown

### 📝 Technical Details

- Added `close()` method to `Elios4YouAPI` class that properly delegates to internal telnet client
- Error message was: `'Elios4YouAPI' object has no attribute 'close'`
- Now cleanly closes telnet connection during integration unload

**Files Changed:**
- `custom_components/4noks_elios4you/api.py` - Added close() method

**All improvements from v0.2.0-beta.1 are included in this release.**

**Full Release Notes:** [docs/releases/v0.2.0-beta.2.md](docs/releases/v0.2.0-beta.2.md)

**Full Changelog:** https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.2.0-beta.1...v0.2.0-beta.2

---

## [0.2.0-beta.1] - 2025-10-12

⚠️ **This is a BETA release** - Please test thoroughly before using in production

### 🐛 Critical Bug Fixes

- **Fixed Sensor Availability** ⭐ MOST IMPORTANT - Sensors now properly show "unavailable" when device is offline instead of displaying stale data
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

**Full Changelog:** https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.1.0...v0.2.0-beta.1

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

[Unreleased]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v1.0.0...HEAD
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
