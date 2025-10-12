# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

No unreleased changes at this time.

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

[Unreleased]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.2.0-beta.2...HEAD
[0.2.0-beta.2]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.2.0-beta.1...v0.2.0-beta.2
[0.2.0-beta.1]: https://github.com/alexdelprete/ha-4noks-elios4you/compare/v0.1.0...v0.2.0-beta.1
[0.1.0]: https://github.com/alexdelprete/ha-4noks-elios4you/releases/tag/v0.1.0
