# Claude Code Development Guidelines

## Critical Initial Steps

> **MANDATORY: At the START of EVERY session, you MUST read this entire CLAUDE.md file.**
>
> This file contains project-specific directives, workflows, and patterns that override default behavior.
> Failure to read this file results in violations of mandatory workflows (e.g., missing release documentation),
> duplicated effort, and broken architectural patterns.

**At every session start, you MUST:**

1. **Read this entire CLAUDE.md file** for project context and mandatory procedures
2. Review recent git commits to understand changes (`git log --oneline -10`)
3. Run `git status` to see uncommitted work

**Key mandatory workflows documented here:**
- **Pre-commit checks** - Run `uvx pre-commit run --all-files` BEFORE every commit
- Release documentation (CHANGELOG.md + docs/releases/)
- Version bumping (manifest.json + const.py)
- Logging patterns (helpers.py functions)
- Error handling (custom exceptions)
- Code quality checks (ruff, ty)

### Fetching GitHub Actions Workflow Run Logs

The GitHub MCP server does not provide a tool to fetch workflow run logs directly. Use this workaround:

1. **Get the workflow run ID** using `gh` CLI:

   ```bash
   gh run list --repo alexdelprete/ha-4noks-elios4you --workflow=test.yml --limit 1 --json databaseId,status,conclusion
   ```

2. **Fetch the logs** using the run ID:

   ```bash
   gh run view <run_id> --repo alexdelprete/ha-4noks-elios4you --log
   ```

3. **Filter for specific output** (e.g., coverage percentage):

   ```bash
   gh run view <run_id> --repo alexdelprete/ha-4noks-elios4you --log 2>&1 | grep "TOTAL"
   ```

**Example - Get latest test coverage:**

```bash
# Step 1: Get latest test run ID
gh run list --repo alexdelprete/ha-4noks-elios4you --workflow=test.yml --limit 1 --json databaseId

# Step 2: Fetch coverage from logs (replace <run_id> with actual ID)
gh run view <run_id> --repo alexdelprete/ha-4noks-elios4you --log 2>&1 | grep "TOTAL"
```

## Project Overview

This is a Home Assistant custom integration for **4-noks Elios4you** energy monitoring devices using Telnet protocol. The device monitors power/energy consumption and photovoltaic production.

This integration is based on and aligned with [ha-sinapsi-alfa](https://github.com/alexdelprete/ha-sinapsi-alfa) and [ha-abb-powerone-pvi-sunspec](https://github.com/alexdelprete/ha-abb-powerone-pvi-sunspec), sharing similar architecture and code quality standards.

## Code Architecture

### Core Components

1. **`__init__.py`** - Integration lifecycle management
   - `async_setup_entry()` - Initialize coordinator and platforms
   - `async_unload_entry()` - Clean shutdown and resource cleanup
   - `async_migrate_entry()` - Config migration logic (v1→v2)
   - Uses `runtime_data` for storing coordinator

1. **`api.py`** - Telnet communication layer
   - `Elios4YouAPI` class handles all Telnet operations
   - Custom exception handling: `TelnetConnectionError`, `TelnetCommandError`
   - Implements connection management and timeout handling

1. **`coordinator.py`** - Data update coordination
   - `Elios4YouCoordinator` manages polling cycles
   - Handles data refresh from API
   - Enforces MIN/MAX_SCAN_INTERVAL constraints

1. **`config_flow.py`** - UI configuration (VERSION = 2)
   - ConfigFlow for initial setup (stores data + options separately)
   - OptionsFlow (Configure button): change scan_interval - auto-reloads via `OptionsFlowWithReload`
   - ReconfigureFlow (3-dot menu > Reconfigure): change name, host, port - auto-reloads

1. **`sensor.py`** - Sensor entity platform (41 sensors)

1. **`switch.py`** - Switch entity platform (1 relay switch)

## Important Patterns

### Error Handling

- Use custom exceptions: `TelnetConnectionError`, `TelnetCommandError`
- Raise exceptions instead of returning `False` for proper availability tracking

### Logging

- Use centralized logging helpers from `helpers.py`:
  - `log_debug(logger, context, message, **kwargs)`
  - `log_info(logger, context, message, **kwargs)`
  - `log_warning(logger, context, message, **kwargs)`
  - `log_error(logger, context, message, **kwargs)`
- Never use f-strings in logger calls (use `%s` formatting)
- Format: `(function_name) [key=value]: message`

### Configuration Split

- `config_entry.data` - Connection config (name, host, port) - changed via Reconfigure flow (3-dot menu)
- `config_entry.options` - Runtime tuning (scan_interval) - changed via Options flow (Configure button)

## Code Quality Standards

**Test Requirements:**

- All tests must pass before pushing
- Maintain 95%+ code coverage per file
- **Tests run in CI only** - Due to complex HA dependencies, run tests via GitHub Actions

#### Running Tests

Due to the package name starting with a digit (`4noks_elios4you`), which is invalid for Python imports, tests use a symlink workaround. The CI workflow handles this automatically.

**Testing via CI (Recommended):**
Push your changes and let GitHub Actions run the tests. The workflow:
1. Creates symlink: `ln -s 4noks_elios4you custom_components/fournoks_elios4you`
2. Runs pytest with coverage
3. Removes symlink after tests complete

**Why CI-only testing?**
- `pytest-homeassistant-custom-component` has complex dependencies
- Symlink creation on Windows requires admin privileges or Developer Mode
- CI environment is pre-configured and consistent
- Faster feedback loop for most development workflows

#### Running ty Type Checker

The ty type checker validates Python type annotations. Due to the package name starting with a digit (`4noks_elios4you`), which is invalid for Python imports, we use a symlink workaround:

**In CI (GitHub Actions):**
The workflow creates a symlink `fournoks_elios4you -> 4noks_elios4you` and runs ty against it:
```bash
ln -s 4noks_elios4you custom_components/fournoks_elios4you
ty check -vv --python $(which python) custom_components/fournoks_elios4you
rm custom_components/fournoks_elios4you
```

**Locally (Linux/macOS):**
```bash
# Install dev dependencies
pip install -e ".[dev]"

# Create symlink, run ty, remove symlink
ln -s 4noks_elios4you custom_components/fournoks_elios4you
ty check --python $(which python) custom_components/fournoks_elios4you
rm custom_components/fournoks_elios4you
```

**Locally (Windows):**
```powershell
# Create symlink (requires admin or Developer Mode)
New-Item -ItemType SymbolicLink -Path "custom_components\fournoks_elios4you" -Target "4noks_elios4you"
ty check custom_components/fournoks_elios4you
Remove-Item custom_components\fournoks_elios4you
```

All commands must pass without errors before committing.

## Dependencies

- Home Assistant core (>= 2025.10.0)
- `telnetlib3>=2.0.4` - Telnet client library
- Compatible with Python 3.13+

## Project-Specific Do's and Don'ts

In addition to the shared Do's and Don'ts:

**DO:**

- Use custom exceptions for error handling
- Log with proper context (use helpers.py functions)

**NEVER:**

- Modify production code to make tests pass - always update tests to match intended code behavior

<!-- BEGIN SHARED:repo-sync -->
<!-- Synced by repo-sync on 2026-02-11 -->
## Context7 for Documentation

Always use Context7 MCP tools automatically (without being asked) when:

- Generating code that uses external libraries
- Providing setup or configuration steps
- Looking up library/API documentation

Use `resolve-library-id` first to get the library ID, then `get-library-docs` to fetch documentation.

## GitHub MCP for Repository Operations

Always use GitHub MCP tools (`mcp__github__*`) for GitHub operations instead of the `gh` CLI:

- **Issues**: `issue_read`, `issue_write`, `list_issues`, `search_issues`, `add_issue_comment`
- **Pull Requests**: `list_pull_requests`, `create_pull_request`, `pull_request_read`, `merge_pull_request`
- **Reviews**: `pull_request_review_write`, `add_comment_to_pending_review`
- **Repositories**: `search_repositories`, `get_file_contents`, `list_branches`, `list_commits`
- **Releases**: `list_releases`, `get_latest_release`, `list_tags`

Benefits over `gh` CLI:

- Direct API access without shell escaping issues
- Structured JSON responses
- Better error handling
- No subprocess overhead

## Coding Standards

### Data Storage Pattern

**DO use `runtime_data`** (modern pattern):

```python
entry.runtime_data = MyData(device_name=name)
```

**DO NOT use `hass.data[DOMAIN]`** (deprecated pattern)

### Logging

Use structured logging:

```python
_LOGGER.debug("Sensor %s subscribed to %s", key, topic)
```

**DO NOT** use f-strings in logger calls (deferred formatting is more efficient)

### Type Hints

Always use type hints for function signatures.

## Pre-Commit Configuration

Linting tools and settings are defined in `.pre-commit-config.yaml`:

| Hook        | Tool                           | Purpose                      |
| ----------- | ------------------------------ | ---------------------------- |
| ruff        | `ruff check --no-fix`          | Python linting               |
| ruff-format | `ruff format --check`          | Python formatting            |
| jsonlint    | `uvx --from demjson3 jsonlint` | JSON validation              |
| yamllint    | `uvx yamllint -d "{...}"`      | YAML linting (inline config) |
| pymarkdown  | `pymarkdown scan`              | Markdown linting             |

All hooks use `language: system` (local tools) with `verbose: true` for visibility.

## Pre-Commit Checks (MANDATORY)

> **CRITICAL: ALWAYS run pre-commit checks before ANY git commit.**
> This is a hard rule - no exceptions. Never commit without passing all checks.

```bash
uvx pre-commit run --all-files
```

Or run individual tools:

```bash
# Python formatting and linting
ruff format .
ruff check . --fix

# Markdown linting
pymarkdown scan .
```

All checks must pass before committing. This applies to ALL commits, not just releases.

### Windows Shell Notes

When running shell commands on Windows, stray `nul` files may be created (Windows null device artifact).
Check for and delete them after command execution:

```bash
rm nul  # if it exists
```

## Testing

> **CRITICAL: NEVER run pytest locally. The local environment cannot be set up correctly for
> Home Assistant integration tests. ALWAYS use GitHub Actions CI to run tests.**

To run tests:

1. Commit and push changes to the repository
1. GitHub Actions will automatically run the test workflow
1. Check the workflow results in the Actions tab or use `mcp__github__*` tools

> **CRITICAL: NEVER modify production code to make tests pass. Always fix the tests instead.**
> Production code is the source of truth. If tests fail, the tests are wrong - not the production code.
> The only exception is when production code has an actual bug that tests correctly identified.

## Quality Scale Tracking (MUST DO)

This integration tracks [Home Assistant Quality Scale][qs] rules in `quality_scale.yaml`.

**When implementing new features or fixing bugs:**

1. Check if the change affects any quality scale rules
1. Update `quality_scale.yaml` status accordingly:
   - `done` - Rule is fully implemented
   - `todo` - Rule needs implementation
   - `exempt` with `comment` - Rule doesn't apply (explain why)
1. Aim to complete all Bronze tier rules first, then Silver, Gold, Platinum

[qs]: https://developers.home-assistant.io/docs/core/integration-quality-scale/

## Release Management - CRITICAL

> **STOP: NEVER create git tags or GitHub releases without explicit user command.**
> This is a hard rule. Always stop after commit/push and wait for user instruction.

**Published releases are FROZEN** - Never modify documentation for released versions.

**Master branch = Next Release** - All commits target the next version with version bumped
in manifest.json and const.py.

### Version Bumping Rules

> **IMPORTANT: Do NOT bump version during a session. All changes go into the CURRENT unreleased version.**

- The version in `manifest.json` and `const.py` represents the NEXT release being prepared
- **NEVER bump version until user commands "tag and release"**
- Multiple features/fixes can be added to the same unreleased version
- Only bump to a NEW version number AFTER the current version is released

### Version Locations (Must Be Synchronized)

1. `custom_components/4noks_elios4you/manifest.json` → `"version": "X.Y.Z"`
1. `custom_components/4noks_elios4you/const.py` → `VERSION = "X.Y.Z"`

### Complete Release Workflow

> **IMPORTANT: Version Validation**
> The release workflow VALIDATES that tag, manifest.json, and const.py versions all match.
> You MUST update versions BEFORE creating the release, not after.

| Step | Tool           | Action                                                                  |
| ---- | -------------- | ----------------------------------------------------------------------- |
| 1    | Edit           | Update `CHANGELOG.md` with version summary                              |
| 2    | Edit           | Ensure `manifest.json` and `const.py` have correct version              |
| 3    | Bash           | Run linting: `uvx pre-commit run --all-files`                           |
| 4    | Bash           | `git add . && git commit -m "..."`                                      |
| 5    | Bash           | `git push`                                                              |
| 6    | **STOP**       | Wait for user "tag and release" command                                 |
| 7    | **CI Check**   | Verify ALL CI workflows pass (see CI Verification below)                |
| 8    | **Checklist**  | Display Release Readiness Checklist (see below)                         |
| 9    | Bash           | `git tag -a vX.Y.Z -m "Release vX.Y.Z"`                                |
| 10   | Bash           | `git push --tags`                                                       |
| 11   | gh CLI         | `gh release create vX.Y.Z --title "vX.Y.Z" --notes "$(RELEASE_NOTES)"` |
| 12   | GitHub Actions | Validates versions match, then auto-uploads ZIP asset                   |
| 13   | Edit           | Bump versions in `manifest.json` and `const.py` to next version         |

### CI Verification (MANDATORY)

> **CRITICAL: Before tagging/releasing, ALWAYS verify ALL CI workflows are passing.**
> Use GitHub MCP tools to list workflow runs, then use `gh` CLI to get detailed logs if needed.
> NEVER proceed if any workflow is failing.

**Verification steps:**

1. Use `mcp__GitHub_MCP_Remote__actions_list` to list recent workflow runs:

   ```text
   actions_list(method="list_workflow_runs", owner="alexdelprete", repo="ha-4noks-elios4you")
   ```

1. Check that ALL workflows show `conclusion: "success"`:
   - Lint workflow
   - Validate workflow
   - Tests workflow

1. If any workflow is failing, use `gh` CLI to get detailed failure logs:

   ```bash
   # View failed run logs (replace <run_id> with actual ID from step 1)
   gh run view <run_id> --log-failed

   # Or view full logs for a specific run
   gh run view <run_id> --log
   ```

1. Fix failing tests/issues, commit, push, and re-verify before proceeding

### Release Notes Format (MANDATORY)

When creating a release, use this format for the release notes:

```markdown
# Release vX.Y.Z

[![GitHub Downloads](https://img.shields.io/github/downloads/alexdelprete/ha-4noks-elios4you/vX.Y.Z/total?style=for-the-badge)](https://github.com/alexdelprete/ha-4noks-elios4you/releases/tag/vX.Y.Z)

**Release Date:** YYYY-MM-DD

**Type:** [Major/Minor/Patch] release - Brief description.

## What's Changed

### ✨ Added
- Feature 1

### 🔄 Changed
- Change 1

### 🐛 Fixed
- Fix 1

**Full Changelog**: https://github.com/alexdelprete/ha-4noks-elios4you/compare/vPREV...vX.Y.Z
```

### Release Readiness Checklist (MANDATORY)

> **When user commands "tag and release", ALWAYS display this checklist BEFORE proceeding.**

```markdown
## Release Readiness Checklist

| Item | Status |
|------|--------|
| Version in `manifest.json` | X.Y.Z |
| Version in `const.py` | X.Y.Z |
| CHANGELOG.md updated | Updated |
| GitHub Actions (lint/test/validate) | PASSING |
| Working tree clean | Clean |
| Git tag | vX.Y.Z created/pushed |
```

Verify ALL items before proceeding with tag creation. If any item fails, fix it first.

## Do's and Don'ts

**DO:**

- Run `uvx pre-commit run --all-files` before EVERY commit
- Read CLAUDE.md at session start
- Use `runtime_data` for data storage (not `hass.data[DOMAIN]`)
- Use `@callback` decorator for message handlers
- Log with `%s` formatting (not f-strings)
- Handle missing data gracefully
- Update both manifest.json AND const.py for version bumps
- Get approval before creating tags/releases

**NEVER:**

- Commit without running pre-commit checks first
- Modify production code to make tests pass - fix the tests instead
- Use `hass.data[DOMAIN][entry_id]` - use `runtime_data` instead
- Shadow Python builtins (A001)
- Use f-strings in logging (G004)
- Create git tags or GitHub releases without explicit user instruction
- Forget to update VERSION in both manifest.json AND const.py
- Use blocking calls in async context
- Close GitHub issues without explicit user instruction

<!-- END SHARED:repo-sync -->

---

# Release History

## v1.0.0 - First Stable Release

**Date:** December 31, 2025
**Claude Model:** Opus 4.5 (claude-opus-4-5-20251101)
**Development Tool:** Claude Code (VSCode Extension)

---

### Overview

First stable v1.0.0 release marking the integration as production-ready. This milestone represents the culmination of extensive development and testing since v0.2.0.

### Key Achievements

- **Home Assistant Quality Scale Platinum Tier** - Full compliance with all tiers including strict typing
- **98% Test Coverage** - 188 tests covering all integration components
- **Full Async I/O** - telnetlib3 for non-blocking telnet operations
- **Connection Pooling** - 25-second reuse window prevents device socket exhaustion
- **Comprehensive Documentation** - Known limitations, troubleshooting, repair notifications

### Documentation Updates

1. **README.md**
   - Added Known Limitations section (single device per instance)
   - Added Troubleshooting section (debug logging, repair notifications, opening issues)
   - Updated Features to include repair notifications and diagnostics

2. **docs/releases/v1.0.0.md** - Comprehensive release notes
3. **CHANGELOG.md** - v1.0.0 section with all changes since v0.2.0

### Breaking Changes

**None** - Migration from any previous version is seamless.

### Files Modified

| File | Changes |
|------|---------|
| `README.md` | Known Limitations, Troubleshooting, Features update |
| `docs/releases/v1.0.0.md` | New release notes |
| `CHANGELOG.md` | v1.0.0 section |
| `CLAUDE.md` | This release history |
| `manifest.json` | version: "1.0.0" |
| `const.py` | VERSION = "1.0.0" |

---

## v0.4.0-beta.3 - Migrate from mypy to ty Type Checker

**Date:** December 29, 2025
**Claude Model:** Opus 4.5 (claude-opus-4-5-20251101)
**Development Tool:** Claude Code (VSCode Extension)

---

### Overview

Migrated from mypy to [ty](https://github.com/astral-sh/ty) (Astral's new Rust-based Python type checker) for faster type checking in CI.

### The Digit-Prefix Problem

The package name `4noks_elios4you` starts with a digit, which is not a valid Python identifier. This causes type checkers to fail when resolving relative imports like `.const`, `.api`, `.helpers`.

**Solution:** Use a symlink workaround in CI:
1. Create symlink: `ln -s 4noks_elios4you custom_components/fournoks_elios4you`
2. Run ty against the symlink: `ty check -vv --python $(which python) custom_components/fournoks_elios4you`
3. Remove symlink after checking

### Files Modified

1. **`.github/workflows/lint.yml`** - Updated ty step with symlink workaround
2. **`pyproject.toml`** - Simplified ty configuration
3. **`README.md`** - Updated CI/CD documentation (changed "mypy" to "ty")
4. **`CLAUDE.md`** - Added detailed instructions for running ty locally

### Why ty Over mypy

- **Speed**: ty is written in Rust, significantly faster than mypy
- **Modern**: Actively developed by Astral (makers of ruff)
- **Consistent**: Same team maintains ruff and ty, unified tooling

---

## v0.4.0-beta.1 - Test Infrastructure & Bug Fixes

**Date:** December 29, 2025
**Claude Model:** Opus 4.5 (claude-opus-4-5-20251101)
**Development Tool:** Claude Code (VSCode Extension)

---

### Test Infrastructure Added

Comprehensive test suite achieving **98% code coverage** across the integration:

**Test Statistics:**
- 188 tests passing
- 7 tests skipped (platform loading tests incompatible with numeric module prefix)
- Coverage: 98% overall (`__init__.py` at 82% due to skipped platform tests)

**Test Files Created:**
- `tests/conftest.py` - Shared fixtures and test configuration
- `tests/test_api.py` - API layer tests (connection, commands, errors)
- `tests/test_config_flow.py` - Config flow, options flow, reconfigure tests
- `tests/test_coordinator.py` - Coordinator and data update tests
- `tests/test_init.py` - Integration lifecycle, migration, device registry tests
- `tests/test_sensor.py` - Sensor entity tests
- `tests/test_switch.py` - Switch entity tests

**Testing Patterns Established:**

1. **Numeric Module Import Workaround:**
   ```python
   import importlib
   _elios4you_api = importlib.import_module("custom_components.4noks_elios4you.api")
   ```

2. **PropertyMock for Read-Only Properties:**
   ```python
   with patch.object(
       type(flow), "config_entry", new_callable=PropertyMock, return_value=mock_entry
   ):
       result = await flow.async_step_init(None)
   ```

3. **Unique ID Mocking for Config Flow:**
   ```python
   flow.async_set_unique_id = AsyncMock()
   flow._abort_if_unique_id_configured = MagicMock()
   ```

### Bug Fix: `async_remove_config_entry_device`

**Problem:** The function incorrectly checked device identifiers:
```python
# WRONG - identifiers is a set of tuples, not strings
if DOMAIN in device_entry.identifiers:
```

**Fix:** Proper tuple check per HA best practices:
```python
# CORRECT - check first element of each tuple
if any(identifier[0] == DOMAIN for identifier in device_entry.identifiers):
```

**Reference:** [HA Integration Quality Scale - Stale Devices](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/stale-devices/)

### CI/CD Enhancements

**GitHub Actions Workflows:**
- `test.yml` - Runs pytest with coverage, uploads to Codecov
- `lint.yml` - Runs ruff format, ruff check, ty type checker
- `validate.yml` - Runs hassfest and HACS validation
- `release.yml` - Creates ZIP on GitHub release publish

---

## v0.4.0-beta.1 - Migrate to telnetlib3 Async Client

**Date:** December 29, 2025
**Claude Model:** Opus 4.5 (claude-opus-4-5-20251101)
**Development Tool:** Claude Code (VSCode Extension)

---

### Overview

This release migrates from bundled synchronous `telnetlib` to `telnetlib3` async client. This eliminates event loop blocking during telnet I/O operations, ensuring Home Assistant remains responsive during polling cycles.

### Problem Identified

**Symptoms:**
- `read_until()` blocked the event loop for up to 5 seconds per command
- Other integrations, automations, and UI updates would freeze during telnet I/O
- Home Assistant responsiveness degraded during polling cycles

**Root Cause:**
The bundled synchronous `telnetlib.Telnet` class performs blocking I/O. Even though `async_get_data()` was marked as `async`, the internal `telnet_get_data()` method called synchronous `read_until()`, which blocked the entire event loop.

### Solution Implemented

**Full Async Migration:**

1. **Replaced bundled telnetlib with telnetlib3** - Using `telnetlib3.open_connection()` for async streams
2. **New `_async_read_until()` method** - Custom async read-until-separator helper for stream-based reading
3. **New `_async_send_command()` method** - Replaces sync `telnet_get_data()` with fully async implementation
4. **Converted connection methods to async** - `_ensure_connected()`, `_safe_close()`, `close()` are now async
5. **Removed E4Utelnet class** - No longer needed with native telnetlib3 usage
6. **Deleted bundled telnetlib** - 672 lines of legacy code removed

### Migration Summary

| Component | Before (Sync) | After (Async) |
|-----------|---------------|---------------|
| Import | `from .telnetlib import Telnet` | `import telnetlib3` |
| Client | `E4Utelnet()` class | `reader, writer` tuple |
| Connect | `E4Uclient.open()` | `await telnetlib3.open_connection()` |
| Write | `E4Uclient.write()` | `writer.write(); await writer.drain()` |
| Read | `E4Uclient.read_until()` | `await _async_read_until()` |
| Close | `E4Uclient.close()` | `await writer.wait_closed()` |
| Is Open | `E4Uclient.is_open()` | `writer is not None and not writer.is_closing()` |

### Preserved Features

All existing functionality preserved:
- ✅ Connection pooling (25-second reuse window)
- ✅ Command retry logic (3 retries, 300ms delay)
- ✅ Race condition prevention via asyncio.Lock
- ✅ Silent timeout detection
- ✅ Same exception handling (TelnetConnectionError, TelnetCommandError)

### Files Modified

1. **`api.py`** - Major rewrite (~80% of file)
   - Removed `E4Utelnet` class
   - Added `_async_read_until()`, `_async_send_command()` methods
   - Converted `_ensure_connected()`, `_safe_close()`, `close()` to async
   - Updated `_get_data_with_retry()` to use `_async_send_command()`
   - Updated `async_get_data()` and `telnet_set_relay()` with await calls
2. **`__init__.py`** - Updated to `await` async `close()` method
3. **`const.py`** - Version bump to 0.4.0-beta.1
4. **`manifest.json`** - Version bump to 0.4.0-beta.1
5. **`telnetlib/__init__.py`** - **Deleted** (bundled sync telnetlib no longer needed)

### Development Approach

**Analysis Phase:**
- Identified event loop blocking from sync `read_until()`
- Researched async telnet alternatives (telnetlib3, aiotelnet, asyncio-telnet)
- Chose telnetlib3 (already a dependency, actively maintained, stable)

**Implementation Phase:**
1. Created migration plan (`idempotent-tickling-crown.md`)
2. Rewrote api.py with async telnetlib3 client
3. Added `_async_read_until()` helper for stream-based reading
4. Converted all connection methods to async
5. Updated `__init__.py` for async close
6. Deleted bundled telnetlib directory
7. Validated with ruff (100% compliance)

**Quality Assurance:**
- Net reduction of 680 lines (+194 / -874)
- Removed 672 lines of bundled telnetlib
- 100% Ruff compliance maintained

### Pattern: Async Telnet with telnetlib3

```python
import telnetlib3

class Elios4YouAPI:
    def __init__(self, ...):
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connection_lock = asyncio.Lock()

    async def _ensure_connected(self) -> None:
        self._reader, self._writer = await asyncio.wait_for(
            telnetlib3.open_connection(self._host, self._port),
            timeout=self._timeout,
        )

    async def _async_read_until(self, separator: bytes, timeout: float) -> bytes:
        buffer = b""
        end_time = asyncio.get_event_loop().time() + timeout
        while separator not in buffer:
            remaining = end_time - asyncio.get_event_loop().time()
            if remaining <= 0:
                return buffer
            chunk = await asyncio.wait_for(self._reader.read(1024), timeout=remaining)
            if not chunk:
                return buffer
            buffer += chunk
        return buffer

    async def _async_send_command(self, cmd: str) -> dict | None:
        self._writer.write((cmd + "\n").encode("utf-8"))
        await self._writer.drain()
        response = await self._async_read_until(b"ready...", self._timeout)
        # Parse response...
```

### Testing Recommendations

1. **Basic connectivity** - Verify connection establishes
2. **Data reading** - Verify @dat, @sta, @inf return correct data
3. **Relay control** - Test ON/OFF commands
4. **Timeout handling** - Disconnect device, verify timeout/retry
5. **Connection reuse** - Verify 25-second pooling still works
6. **Long-term stability** - Run for 24+ hours
7. **HA responsiveness** - Verify UI remains responsive during polling

**Full Release Notes:** [docs/releases/v0.4.0-beta.1.md](docs/releases/v0.4.0-beta.1.md)

---

## v0.3.0-beta.1 - Connection Pooling Fix

**Date:** December 29, 2025
**Claude Model:** Opus 4.5 (claude-opus-4-5-20251101)
**Development Tool:** Claude Code (VSCode Extension)

---

### Overview

This beta release addresses a critical runtime issue where the Elios4You device becomes "deaf" (unresponsive to telnet commands) 50-60 times per day. The fix implements connection pooling to prevent socket exhaustion on the embedded device.

### Problem Identified

**Symptoms:**
- Device becomes unresponsive 50-60 times per day
- Device is pingable but telnet doesn't respond
- All entities become stale
- Only fix is WiFi reconnection

**Root Causes (Deep Analysis):**
1. **Socket Exhaustion** - 2 sockets per poll (check_port + connection) = ~120 sockets/hour
2. **No Connection Reuse** - Fresh connection every 30-60 seconds
3. **TIME_WAIT Accumulation** - Sockets linger 2 minutes, overwhelms device
4. **Silent Timeouts** - `read_until()` returns partial data without exception
5. **Race Conditions** - Polling + switch commands compete for single connection
6. **Global Timeout Mutation** - `socket.setdefaulttimeout()` affects all sockets

### Solution Implemented

**Connection Pooling Architecture:**

1. **`asyncio.Lock`** - Serializes all telnet operations (polling and switch commands)
2. **25-second Connection Reuse** - Existing connections reused within window
3. **`_safe_close()`** - Graceful close with buffer draining and TCP shutdown
4. **`_is_connection_valid()`** - Validates connection before reuse
5. **`_ensure_connected()`** - Opens connection only when needed
6. **Silent Timeout Detection** - Detects incomplete responses in `telnet_get_data()`
7. **Socket-Specific Timeout** - Fixed to use `sock.settimeout()` instead of global

**Expected Results:**
| Metric | Before | After |
|--------|--------|-------|
| Sockets per poll | 2 | 0-1 (reuse) |
| TIME_WAIT accumulation | 120/hour | ~2/hour |
| Race condition risk | High | None (locked) |
| Device "deaf" events | 50-60/day | ~0 |

### Other Changes

- **Removed Redundant Update Listener** - Aligned with ha-sinapsi-alfa; `OptionsFlowWithReload` handles reloads automatically
- **Fixed Ruff SIM105** - Used `contextlib.suppress()` instead of try-except-pass

### Files Modified

1. **`api.py`** - Major connection pooling implementation
2. **`__init__.py`** - Removed redundant update listener
3. **`const.py`** - Version bump to 0.3.0-beta.1
4. **`manifest.json`** - Version bump to 0.3.0-beta.1
5. **`.gitignore`** - Added build/ directory

### Development Approach

**Analysis Phase:**
- Deep analysis of codebase for socket/connection issues
- Compared with ha-sinapsi-alfa for patterns
- Created detailed plan (saved at `C:\Users\aless\.claude\plans\generic-doodling-wren.md`)

**Implementation Phase:**
1. Added connection lock and tracking infrastructure
2. Implemented connection reuse methods
3. Refactored async_get_data() and telnet_set_relay()
4. Fixed silent timeout detection
5. Fixed global timeout mutation
6. Removed redundant update listener

**Quality Assurance:**
- Ruff validation (100% compliance)
- Fixed SIM105 linting errors with contextlib.suppress()

### Lessons Learned

**Socket Exhaustion on Embedded Devices:**
- Embedded devices have limited socket backlog
- TIME_WAIT accumulation can exhaust resources
- Connection pooling is essential for frequent polling
- Always use socket-specific timeouts, not global

**Pattern: Connection Pooling for Telnet:**
```python
class Elios4YouAPI:
    CONNECTION_REUSE_TIMEOUT: float = 25.0

    def __init__(self, ...):
        self._connection_lock = asyncio.Lock()
        self._last_activity: float = 0.0

    async def async_get_data(self) -> bool:
        async with self._connection_lock:
            self._ensure_connected()
            # ... operations ...
```

**Full Release Notes:** [docs/releases/v0.3.0-beta.1.md](docs/releases/v0.3.0-beta.1.md)

---

## v0.2.0 - Official Stable Release

**Date:** October 15, 2025
**Claude Model:** Sonnet 4.5 (claude-sonnet-4-5-20250929)
**Development Tool:** Claude Code (VSCode Extension)

---

### Overview

This is the **official stable release** of v0.2.0, marking the successful completion of the beta testing cycle. This release includes all improvements from beta.1, beta.2, and beta.3, plus dependency updates to ensure compatibility with Home Assistant 2025.10.x and Python 3.13.

### What Was Accomplished

All changes from the beta cycle are now production-ready:

- ✅ **From beta.1:** Critical bug fixes (sensor availability, unload errors, async/await), custom exceptions, type hints, code quality (100% ruff compliance)
- ✅ **From beta.2:** Hotfix for integration unload (added `close()` method)
- ✅ **From beta.3:** Architecture alignment (logging system, helpers.py, core refactoring)
- ✅ **New in v0.2.0:** Updated dependencies for HA 2025.10.x and Python 3.13 compatibility

### Syncing with ABB Power-One Repository

This release includes updates synced from today's commits (Oct 15, 2025) in the reference ABB Power-One PVI SunSpec repository:

**Commits Applied:**
1. **1668962** - "Fix lint workflow: upgrade to Python 3.13 for HA 2025.10.2 compatibility"
   - Updated `.github/workflows/lint.yml` to use Python 3.13
   - Reason: HA 2025.10.2 requires Python >=3.13.2

2. **274e876** - "Update dependencies to latest versions"
   - Updated `requirements.txt`: homeassistant 2025.10.2, pip constraint <25.3
   - Updated `hacs.json`: homeassistant requirement 2025.10.0+
   - Note: Kept telnetlib3>=2.0.4 (no updates needed, different from pymodbus)

**Process:**
1. Cloned ABB repository and reviewed recent commits
2. Identified applicable changes (dependency updates, Python version)
3. Adapted changes for Elios4you integration (telnet vs modbus differences)
4. Updated all relevant files following the same patterns
5. Created comprehensive release documentation

### Release Notes Best Practices

**Important Documentation Standard Established:**

When creating release notes, we follow this pattern:

1. **Official/Stable Releases (e.g., v0.2.0):**
   - Document ALL changes since the LAST STABLE release (not just since last beta)
   - Example: v0.2.0 includes everything from v0.1.0 → v0.2.0
   - Provides complete upgrade path for users who skip beta versions
   - Ensures users upgrading from stable-to-stable see the full picture

2. **Beta Releases (e.g., v0.2.0-beta.1, v0.2.0-beta.2):**
   - Document INCREMENTAL changes from the previous beta
   - Example: beta.2 only documents what changed since beta.1
   - Helps beta testers understand what's new in each iteration
   - Detailed, focused release notes for testing validation

3. **File Structure:**
   - Each release gets its own file: `docs/releases/vX.Y.Z.md`
   - CHANGELOG.md contains summaries with links to detailed release notes
   - Maintain consistency between CHANGELOG and detailed release notes

**Why This Matters:**
- Users on stable versions (v0.1.0) need to see everything that changed when upgrading to v0.2.0
- Beta testers need incremental notes to validate specific changes
- Clear documentation prevents confusion and missed features/fixes
- Provides historical record of project evolution

**This Practice Was Applied:**
- `docs/releases/v0.2.0.md` includes ALL changes from v0.1.0 → v0.2.0
- `docs/releases/v0.2.0-beta.X.md` files contain incremental changes
- CHANGELOG.md follows the same pattern
- Both stable and beta users have appropriate documentation

### Files Modified Summary

**Code Changes:**
1. `.github/workflows/lint.yml` - Python 3.13 update
2. `requirements.txt` - Dependency updates
3. `hacs.json` - HA requirement update
4. `custom_components/4noks_elios4you/manifest.json` - Version 0.2.0
5. `custom_components/4noks_elios4you/const.py` - VERSION constant 0.2.0

**Documentation Changes:**
1. `docs/releases/v0.2.0.md` - Comprehensive official release notes (NEW)
2. `CHANGELOG.md` - v0.2.0 summary with all changes since v0.1.0
3. `CLAUDE.md` - This section documenting the release process
4. `docs/releases/README.md` - Updated with best practices

### Version Number Management

**CRITICAL: When releasing any version, you MUST update version numbers in THREE places:**

1. **`custom_components/4noks_elios4you/manifest.json`** - `"version"` field
2. **`custom_components/4noks_elios4you/const.py`** - `VERSION` constant (line 13)
3. **Git tag** - When pushing the release

**Why This Matters:**
- `manifest.json` - Used by Home Assistant and HACS for version tracking
- `const.py` VERSION - Displayed in logs and startup message for debugging
- Git tag - Marks the release in version control and triggers GitHub release

**Example for v0.2.0:**
```python
# In manifest.json
"version": "0.2.0"

# In const.py (line 13)
VERSION = "0.2.0"

# Git tag
git tag -a v0.2.0 -m "Release v0.2.0"
```

**Release Checklist:**
- [ ] Updated manifest.json version
- [ ] Updated const.py VERSION constant
- [ ] Created comprehensive release notes in docs/releases/
- [ ] Updated CHANGELOG.md
- [ ] Run pre-commit: `uvx pre-commit run --all-files` (MUST pass)
- [ ] Commit all changes with descriptive message
- [ ] Push commit to GitHub
- [ ] Verify GitHub Actions pass (lint/test/validate)
- [ ] Present RRC to user and get approval
- [ ] Create annotated git tag
- [ ] Push tag to GitHub
- [ ] Create GitHub release

### Development Approach

**Analysis Phase:**
- Monitored ABB Power-One repository for updates
- Identified today's commits (Oct 15, 2025)
- Analyzed applicability to Elios4you integration
- Planned comprehensive release documentation

**Implementation Phase:**
1. Updated GitHub workflow for Python 3.13
2. Updated development dependencies
3. Updated HACS configuration
4. Bumped version to 0.2.0 (stable)
5. Created comprehensive release documentation

**Documentation Phase:**
1. Created `docs/releases/v0.2.0.md` with ALL changes since v0.1.0
2. Updated CHANGELOG.md with complete summary
3. Updated CLAUDE.md with release process and best practices
4. Updated `docs/releases/README.md` with documentation standards

**Quality Assurance:**
- Ruff validation (100% compliance maintained)
- Documentation consistency verified
- Version numbers updated everywhere
- Release notes cross-referenced correctly

### Lessons Learned

**What Worked Exceptionally Well:**

1. **Beta Testing Cycle**
   - Three beta releases allowed thorough validation
   - Each beta focused on specific improvements
   - Community feedback informed stable release
   - No surprises in stable release

2. **Reference Implementation Pattern**
   - Continuing to sync with ABB integration ensures best practices
   - Easy to identify and apply relevant updates
   - Both integrations benefit from shared knowledge

3. **Comprehensive Documentation**
   - Release notes best practices now documented
   - Clear distinction between stable and beta notes
   - Users have complete upgrade information
   - Future releases can follow this template

4. **AI-Assisted Development**
   - Claude Code effectively managed complex release process
   - Maintained consistency across multiple documentation files
   - Caught details that might be missed manually
   - Human oversight ensured quality and accuracy

### Future Considerations

**Staying Aligned with ABB Power-One:**
- Monitor ABB repository regularly for updates
- Apply relevant patterns and fixes promptly
- Maintain documentation of what's been synced
- Continue benefiting from battle-tested improvements

**Ongoing Maintenance:**
- Watch for Home Assistant core updates
- Keep dependencies current
- Monitor community feedback
- Address issues promptly

---

## v0.2.0-beta.3 - Architecture Alignment and Logging Standardization

**Date:** October 13, 2025
**Claude Model:** Sonnet 4.5 (claude-sonnet-4-5-20250929)
**Development Tool:** Claude Code (VSCode Extension)

---

### Overview

This release continues the alignment with ABB Power-One PVI SunSpec v4.1.5, focusing on architecture patterns and logging standardization across the entire codebase. This was a comprehensive internal refactoring with no user-facing feature changes.

### What Was Accomplished

- ✅ Created standardized logging system with `helpers.py` module
- ✅ Migrated ALL Python files to use contextual logging functions (~50 logging calls updated)
- ✅ Refactored `__init__.py` core integration lifecycle patterns
- ✅ Simplified RuntimeData structure (removed redundant update_listener field)
- ✅ Converted sync functions to use `@callback` decorator correctly
- ✅ Updated reload pattern to non-blocking `async_schedule_reload()`
- ✅ Added migration infrastructure with `async_migrate_entry()` function
- ✅ Unified host validation using shared helpers function
- ✅ Maintained 100% ruff compliance throughout refactoring

### Key Architectural Changes

#### 1. Standardized Logging System

**Created `helpers.py` Module:**
```python
def log_debug(logger: logging.Logger, context: str, message: str, **kwargs: Any) -> None:
    """Standardized debug logging with context."""
    context_str = f"({context})"
    if kwargs:
        context_parts = [f"{k}={v}" for k, v in kwargs.items()]
        context_str += f" [{', '.join(context_parts)}]"
    logger.debug("%s: %s", context_str, message)
```

**Migration Pattern:**
- **Old:** `_LOGGER.debug(f"Connecting to {host}:{port}")`
- **New:** `log_debug(_LOGGER, "async_connect", "Connecting to device", host=host, port=port)`

**Benefits:**
- Always know which function logged the message
- Structured context data (searchable, filterable)
- No f-strings in logging (better performance)
- Consistent format: `(function_name) [key=value]: message`

#### 2. Core Integration Lifecycle Refactoring

**RuntimeData Simplification:**
```python
# OLD
@dataclass
class RuntimeData:
    coordinator: DataUpdateCoordinator
    update_listener: Callable  # Redundant!

# NEW
@dataclass
class RuntimeData:
    coordinator: DataUpdateCoordinator  # Clean and simple
```

**Update Listener Pattern:**
```python
# OLD (3 lines)
update_listener = config_entry.add_update_listener(async_reload_entry)
config_entry.async_on_unload(update_listener)
config_entry.runtime_data = RuntimeData(coordinator, update_listener)

# NEW (1 line)
config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))
config_entry.runtime_data = RuntimeData(coordinator)
```

**Device Registry Function:**
```python
# OLD
async def async_update_device_registry(...):
    # Incorrectly marked as async
    device_registry.async_get_or_create(...)

# NEW
@callback
def async_update_device_registry(...):
    # Correctly marked as sync with @callback
    device_registry.async_get_or_create(...)
```

**Reload Entry Function:**
```python
# OLD
async def async_reload_entry(...):
    await hass.config_entries.async_reload(...)

# NEW
@callback
def async_reload_entry(...):
    hass.config_entries.async_schedule_reload(...)  # Non-blocking
```

#### 3. Migration Infrastructure

Added future-proof migration function:
```python
async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries."""
    log_debug(_LOGGER, "async_migrate_entry", "Migrating config entry", version=config_entry.version)

    # Future migrations will be added here as needed
    # Example pattern included in comments

    return True
```

### Files Modified Summary

1. **`helpers.py`** (NEW) - 150 lines
   - Standardized logging functions
   - Host validation utility
   - Full docstrings with examples

2. **`__init__.py`** - 50 lines modified
   - RuntimeData simplified
   - Functions decorated with `@callback`
   - Migration infrastructure added
   - 5 logging calls updated

3. **`api.py`** - 100 lines modified
   - ~30 logging calls updated
   - Removed all f-strings from logs
   - Context added to all log messages

4. **`config_flow.py`** - 20 lines modified
   - Host validation moved to helpers
   - 5 logging calls updated
   - Removed code duplication

5. **`coordinator.py`** - 15 lines modified
   - 4 logging calls updated
   - Clean context for all logs

6. **`switch.py`** - 10 lines modified
   - 4 logging calls updated
   - Better structured context

7. **`sensor.py`** - 10 lines modified
   - 2 logging calls updated
   - Consolidated debug logging

8. **`manifest.json`** - 1 line
   - Version: v0.2.0-beta.3

### ABB v4.1.5 Pattern Alignment Complete

| Pattern | Status | Notes |
|---------|--------|-------|
| Contextual logging helpers | ✅ Complete | All files migrated |
| `@callback` for sync operations | ✅ Complete | device_registry, reload_entry |
| Non-blocking reload pattern | ✅ Complete | async_schedule_reload() |
| Simplified RuntimeData | ✅ Complete | Only stores coordinator |
| Migration infrastructure | ✅ Complete | async_migrate_entry() added |
| Clean error propagation | ✅ Complete | From v0.2.0-beta.1 |
| Custom exceptions | ✅ Complete | From v0.2.0-beta.1 |
| Type hints | ✅ Complete | From v0.2.0-beta.1 |

### Development Approach

**Analysis Phase:**
- Compared `__init__.py` between both integrations line-by-line
- Identified key differences in patterns and structure
- Examined helpers.py from ABB integration
- Created detailed comparison matrix

**Implementation Phase:**
1. Created helpers.py with standardized logging
2. Updated __init__.py structure and decorators
3. Migrated logging across all 6 Python files
4. Updated manifest and documentation
5. Validated with ruff (100% compliance maintained)

**Quality Assurance:**
- No breaking changes
- Zero new warnings
- All existing functionality preserved
- Comprehensive documentation created

### Testing Recommendations

1. **Integration Lifecycle:**
   - Install/unload/reload - verify no errors
   - Check debug logs for new format

2. **Logging Verification:**
   - Enable debug logging
   - Verify format: `(function_name) [context]: message`
   - Confirm logs are more actionable

3. **Normal Operations:**
   - Sensor updates continue working
   - Switch operations function correctly
   - Config flow behaves normally

### Lessons Learned

**What Worked Well:**
- Systematic file-by-file approach
- Using ABB v4.1.5 as reference throughout
- Breaking work into logical phases (helpers → __init__ → all other files)
- Todo list tracking for complex multi-file refactoring

**What Could Be Improved:**
- Could have split into multiple smaller releases
- More inline comments explaining pattern choices
- Unit tests would validate refactoring safety

### Future Considerations

Now that the architecture is fully aligned with ABB v4.1.5, future enhancements can benefit from:
- Consistent patterns across both integrations
- Easier maintenance when HA patterns evolve
- Shared learning between the two projects
- Professional logging for troubleshooting

---

## v0.2.0-beta.1 - Code Quality and Reliability Improvements

**Date:** October 12, 2025
**Claude Model:** Sonnet 4.5 (claude-sonnet-4-5-20250929)
**Development Tool:** Claude Code (VSCode Extension)

---

## Overview

This document provides transparency about how Claude AI assisted in the development of v0.2.0-beta.1. The goal was to align the 4noks-elios4you integration with the code quality, reliability improvements, and best practices from the ABB Power-One PVI SunSpec integration v4.1.5.

### What Was Accomplished

- ✅ Fixed critical sensor availability bug (sensors now show "unavailable" when device offline)
- ✅ Fixed integration unload KeyError
- ✅ Fixed missing await in reload function
- ✅ Removed incorrect pymodbus dependency
- ✅ Created custom telnet-specific exception classes
- ✅ Added comprehensive type hints throughout codebase
- ✅ Improved error handling with proper context
- ✅ Cleaned up code and removed technical debt
- ✅ Achieved 100% ruff compliance
- ✅ Modernized code to follow HA 2025.3.0+ patterns

---

## Context & Motivation

### The Challenge

The 4noks-elios4you integration was originally based on the ABB Power-One PVI SunSpec integration's architecture but:

1. Uses **telnet protocol** instead of Modbus/pymodbus
2. Had diverged from the reference implementation over time
3. Suffered from the same issues that were fixed in ABB v4.1.5
4. Lacked the error handling improvements that made ABB sensors properly show "unavailable" state

### The Request

The user (@alexdelprete) requested:

> "this project is based on https://github.com/alexdelprete/ha-abb-powerone-pvi-sunspec, but it doesn't use pymodbus to get data, it uses telnet protocol. I want you to analyze all its codebase and compare it to https://github.com/alexdelprete/ha-abb-powerone-pvi-sunspec, particularly the v4.1.5 that contains a lot of fixes and improvements and propose a plan to align it."

### Why This Approach Works

Using a proven reference implementation (ABB v4.1.5) as a template allowed us to:
- Apply battle-tested fixes to similar problems
- Maintain consistency across the developer's integrations
- Avoid reinventing solutions to already-solved problems
- Benefit from 6 beta releases worth of refinement in ABB v4.1.5

---

## Analysis Process

### Step 1: Comprehensive Codebase Analysis

**Elios4you Integration:**
- Read all Python files in `custom_components/4noks_elios4you/`
- Analyzed: `__init__.py`, `api.py`, `coordinator.py`, `sensor.py`, `switch.py`, `config_flow.py`, `const.py`
- Examined `manifest.json` for dependencies and configuration
- Reviewed project structure and telnet implementation

**ABB Power-One Integration v4.1.5:**
- Fetched and analyzed via WebFetch tool:
  - `__init__.py` - Integration lifecycle management
  - `coordinator.py` - Data update coordinator patterns
  - `sensor.py` - Entity implementation
  - `config_flow.py` - Configuration flow with validation
  - `api.py` - API error handling and exceptions
- Retrieved release notes to understand what was fixed and why
- Identified 6 beta releases leading to v4.1.5, indicating thorough testing

### Step 2: Comparative Analysis

Created a detailed comparison matrix:

| Aspect | Elios4you (Before) | ABB v4.1.5 | Gap Identified |
|--------|-------------------|------------|----------------|
| Error Handling | Returns `False` on failure | Raises exceptions | Critical - causes stale data |
| Exceptions | Generic `ConnectionError` | Custom exceptions with context | Need telnet-specific versions |
| Unload Logic | Complex with `hass.data` management | Simplified, relies on core | Potential KeyError |
| Reload Pattern | `async_schedule_reload()` without await | `async_reload()` with await | Missing await warning |
| Dependencies | Imports pymodbus (unused) | Only imports what's needed | Incorrect dependency |
| Type Hints | Basic | Comprehensive | Need improvement |
| Code Style | Mixed patterns | Consistent ruff-formatted | Need cleanup |

### Step 3: Release Notes Analysis

Analyzed ABB v4.1.5 release notes to understand:
- **Why** each fix was important
- **How** it was implemented
- **What** testing was done (6 beta releases)
- User-facing impact of each change

This revealed the sensor availability fix was the most critical improvement.

---

## Implementation Strategy

### Phase 1: Critical Bug Fixes (Highest Priority)

These fixes directly impact functionality and user experience:

#### 1. Sensor Availability Fix
**The Core Problem:**
```python
# OLD CODE (Elios4you v0.1.0)
async def async_get_data(self):
    if self.check_port():
        try:
            # ... fetch data ...
            return True
        except:
            return False  # ⚠️ Silent failure!
    else:
        raise ConnectionError(...)  # Only if check_port fails
```

**Why This Was Wrong:**
- Exceptions inside the `try` block were caught and returned `False`
- Coordinator didn't know device was offline
- Sensors kept displaying last known values
- Users saw "1.5kW production" at midnight!

**The Fix:**
```python
# NEW CODE (v0.2.0-beta.1)
async def async_get_data(self) -> bool:
    if not self.check_port():
        raise TelnetConnectionError(...)  # Clear signal

    try:
        # ... fetch data ...
        return True
    except (TimeoutError, OSError) as err:
        raise TelnetConnectionError(...) from err  # Propagate!
    except Exception as err:
        raise TelnetCommandError(...) from err
```

**Key Decisions:**
- Create telnet-specific exceptions (not reuse pymodbus ones)
- Always raise on failure (never return `False`)
- Include context in exceptions (host, port, command)
- Use proper exception chaining (`from err`)

#### 2. Integration Unload Fix

**The Problem:**
```python
# OLD CODE
if config_entry.entry_id in hass.data[DOMAIN]:
    hass.data[DOMAIN].pop(config_entry.entry_id)  # KeyError if not present!
```

**The Fix:**
```python
# NEW CODE - Let HA core handle cleanup
if unload_ok:
    try:
        coordinator = config_entry.runtime_data.coordinator
        if coordinator and coordinator.api:
            coordinator.api.close()
    except Exception as err:
        _LOGGER.error("Error closing API connection: %s", err)
```

#### 3. Reload Function Fix

**The Problem:**
```python
# OLD CODE
async def async_reload_entry(...):
    await hass.config_entries.async_schedule_reload(...)  # Wrong method!
```

**The Fix:**
```python
# NEW CODE
async def async_reload_entry(...) -> None:  # Added return type
    await hass.config_entries.async_reload(config_entry.entry_id)
```

#### 4. Dependency Cleanup

**The Problem:**
```python
# config_flow.py
from pymodbus.exceptions import ConnectionException  # Wrong!
```

**The Fix:**
```python
# config_flow.py
from .api import TelnetConnectionError, TelnetCommandError
```

### Phase 2: Code Quality Improvements

#### Enhanced Error Handling

Created context-rich exception classes:

```python
class TelnetConnectionError(Exception):
    """Exception raised when telnet connection fails."""

    def __init__(self, host: str, port: int, timeout: int, message: str = "") -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.message = message or f"Failed to connect to {host}:{port} (timeout: {timeout}s)"
        super().__init__(self.message)
```

Benefits:
- Debugging is easier (know exactly what failed)
- Better error messages in logs
- Can catch specific errors if needed
- Professional exception hierarchy

#### Logging Improvements

**Before:**
```python
_LOGGER.debug(f"Check_Port: opening socket on {self._host}:{self._port} with a {sock_timeout}s timeout {datetime.now()}")
```

**After:**
```python
_LOGGER.debug("Check_Port: opening socket on %s:%s with %ss timeout", self._host, self._port, sock_timeout)
```

Benefits:
- Faster (no f-string formatting if debug disabled)
- No redundant timestamps (HA adds them automatically)
- Cleaner log output
- Standard Python logging best practice

#### Type Hints

Added comprehensive type hints throughout:
- All function signatures
- Return types
- Parameter types
- Better IDE autocomplete
- Catches bugs at development time

### Phase 3: Validation

#### Automated Checks

```bash
# Ran ruff for linting
ruff check custom_components/4noks_elios4you/
# Result: All checks passed! ✅

# Ran ruff for formatting
ruff format custom_components/4noks_elios4you/
# Result: 2 files reformatted, 6 files left unchanged
```

#### Manual Review

- Verified all changes aligned with plan
- Checked that telnet-specific logic was preserved
- Ensured no functionality was removed
- Validated exception handling flow
- Confirmed backwards compatibility

---

## Key Technical Decisions

### Decision 1: Custom Exceptions vs Reusing pymodbus Exceptions

**Options Considered:**
1. Keep using generic `ConnectionError`
2. Import and adapt pymodbus exceptions
3. Create telnet-specific exceptions

**Decision:** Create telnet-specific exceptions

**Reasoning:**
- Telnet protocol has different failure modes than Modbus
- Clearer code when reading `TelnetConnectionError` vs generic errors
- No unnecessary dependency on pymodbus
- Can include telnet-specific context (command, response)
- Professional and maintainable

### Decision 2: When to Raise vs Return

**Old Pattern:**
```python
try:
    # operation
    return True/False
except:
    return False
```

**New Pattern:**
```python
try:
    # operation
    return True
except KnownError as err:
    raise SpecificException(...) from err
```

**Reasoning:**
- Coordinator expects exceptions for unavailable state
- Exceptions provide better error context
- Follows Home Assistant patterns
- Matches ABB v4.1.5 implementation
- No silent failures

### Decision 3: Unload Simplification

**Decision:** Remove manual `hass.data[DOMAIN]` management

**Reasoning:**
- HA core handles `runtime_data` cleanup automatically
- Reduces chance of KeyError
- Less code to maintain
- Modern HA pattern (post-2024.6)
- Matches ABB v4.1.5

### Decision 4: Minimal Changes to Telnet Logic

**Decision:** Don't refactor telnet implementation unless necessary

**Reasoning:**
- Telnet code works and is device-specific
- Focus on alignment, not rewrite
- Preserve knowledge of Elios4you protocol
- Reduce risk of breaking changes
- Can be optimized in future release

### Decision 5: Beta Release

**Decision:** Release as v0.2.0-beta.1, not v0.2.0

**Reasoning:**
- Significant changes to error handling
- Need real-world testing with devices
- ABB v4.1.5 had 6 beta releases for similar changes
- Responsible release practice
- Users can opt-in to testing

---

## Implementation Methodology

### Tools Used

1. **Read Tool** - Read existing code files
2. **WebFetch Tool** - Fetch ABB integration files from GitHub
3. **Grep Tool** - Search for patterns across files
4. **Glob Tool** - Find files by pattern
5. **Edit Tool** - Make surgical code changes
6. **Write Tool** - Create new files (release notes)
7. **Bash Tool** - Run ruff, check git status

### Workflow

1. **Analysis Phase** (Read-only)
   - Read all Elios4you files
   - Fetch ABB v4.1.5 files
   - Compare implementations
   - Identify gaps

2. **Planning Phase** (Read-only)
   - Create detailed alignment plan
   - Prioritize by impact
   - Present plan to user
   - Get approval

3. **Implementation Phase** (Modifications)
   - Phase 1: Critical fixes (sensor availability, unload, reload, dependencies)
   - Phase 2: Code quality (error handling, type hints, cleanup)
   - Phase 3: Validation (ruff checks, formatting)
   - Phase 4: Documentation (this file, release notes)

4. **Validation Phase**
   - Run ruff linter (passed ✅)
   - Run ruff formatter (formatted 2 files)
   - Review diffs
   - Update manifest version

### Quality Assurance

- **No Breaking Changes:** Maintained full backwards compatibility
- **Ruff Compliance:** 100% pass rate
- **Type Safety:** Comprehensive type hints added
- **Error Handling:** All error paths covered
- **Documentation:** Extensive release notes and this file

---

## Testing Recommendations

### Critical Tests (Must Do)

1. **Device Offline Test** ⭐ **MOST IMPORTANT**
   ```
   Action: Disconnect Elios4you device from network
   Expected: Sensors show "unavailable" state
   Expected: No stale data displayed
   Expected: Logs show TelnetConnectionError

   Action: Reconnect device
   Expected: Sensors recover and show current values
   Expected: No errors in logs
   ```

2. **Integration Reload Test**
   ```
   Action: Reload integration via UI
   Expected: Clean reload with no errors
   Expected: No KeyError in logs
   Expected: Sensors continue working
   ```

3. **Integration Unload Test**
   ```
   Action: Remove integration
   Expected: Clean unload with no errors
   Expected: No KeyError in logs
   Expected: API connection properly closed
   ```

### Normal Operation Tests

4. **Sensor Updates**
   - Verify all sensors update at configured interval
   - Check data accuracy against device display
   - Verify calculated sensors (self-consumption) are correct

5. **Switch Entity**
   - Test relay ON/OFF commands
   - Verify state updates immediately
   - Check error handling if command fails

6. **Config Flow**
   - Test adding new integration instance
   - Verify connection validation works
   - Check error messages are clear and helpful
   - Test options flow (changing host, port, interval)

### Edge Cases

7. **Intermittent Connection**
   - Simulate flaky network
   - Verify sensors alternate between available/unavailable correctly

8. **Invalid Responses**
   - Test with device returning malformed data
   - Verify graceful error handling

9. **Multiple Instances**
   - Test with multiple Elios4you devices
   - Verify no interference between instances

### Performance Tests

10. **Long-term Stability**
    - Monitor for 24+ hours
    - Check for memory leaks
    - Verify day/night transitions handle correctly

---

## Challenges Encountered

### Challenge 1: Understanding Telnet Protocol Specifics

**Issue:** The Elios4you telnet protocol is undocumented and reverse-engineered.

**Solution:**
- Carefully preserved existing telnet implementation
- Only modified error handling paths
- Didn't change protocol commands or parsing logic

### Challenge 2: Balancing Alignment with Specificity

**Issue:** ABB uses Modbus, Elios4you uses telnet - can't directly copy code.

**Solution:**
- Understood the *principles* behind ABB fixes
- Adapted the patterns for telnet communication
- Created telnet-specific exception classes
- Maintained the spirit of improvements while respecting protocol differences

### Challenge 3: Ensuring No Breaking Changes

**Issue:** Users have existing configs and automations.

**Solution:**
- Only changed internal implementation
- Maintained all public APIs
- Kept all sensor entities unchanged
- Preserved config flow behavior
- Beta release for validation

---

## Files Modified - Technical Details

### api.py (Major Changes)

**Lines Changed:** ~150 lines modified/added
**Key Changes:**
- Added exception classes (lines 17-36)
- Rewrote `async_get_data()` (lines 196-295)
- Improved `check_port()` logging
- Better error handling in `telnet_get_data()`
- Type hints throughout

**Risk Level:** Medium (core functionality)
**Testing Priority:** High

### __init__.py (Moderate Changes)

**Lines Changed:** ~50 lines modified/removed
**Key Changes:**
- Simplified `async_unload_entry()` (lines 111-133)
- Fixed `async_reload_entry()` (lines 136-140)
- Removed commented code (25 lines deleted)
- Added type hints
- Improved logging

**Risk Level:** Low (lifecycle management)
**Testing Priority:** Medium

### config_flow.py (Minor Changes)

**Lines Changed:** ~15 lines modified
**Key Changes:**
- Removed pymodbus import (line 21 deleted)
- Added custom exception imports (line 22)
- Updated `get_unique_id()` type hints and exception handling (lines 74-88)

**Risk Level:** Low (config flow)
**Testing Priority:** Low

### manifest.json (Version Update)

**Lines Changed:** 1 line
**Key Changes:**
- Version: 0.1.0 → 0.2.0-beta.1

**Risk Level:** None
**Testing Priority:** None

---

## Future Considerations

### Potential Enhancements for v0.3.0

1. **Connection Pooling**
   - Current: Opens/closes connection for each request
   - Future: Keep connection open, add health monitoring
   - Benefit: Faster updates, less overhead
   - Complexity: Medium
   - Based on: ABB v4.1.5 connection management patterns

2. **Diagnostic Sensors**
   - Add sensors for:
     - Last successful update timestamp
     - Update failure count
     - Connection status
     - API response time
   - Benefit: Better troubleshooting
   - Complexity: Low

3. **Advanced Error Recovery**
   - Exponential backoff on connection failures
   - Circuit breaker pattern for persistent failures
   - Benefit: More robust operation
   - Complexity: Medium

4. **Config Validation**
   - Validate IP/hostname format more strictly
   - Test connection during config before saving
   - Benefit: Better user experience
   - Complexity: Low

5. **Device Discovery**
   - Auto-discover Elios4you devices on network
   - Similar to other HA integrations
   - Benefit: Easier setup
   - Complexity: High (requires understanding mDNS/discovery protocol)

### Monitoring & Maintenance

1. **Watch for HA Core Updates**
   - Monitor deprecation warnings
   - Update to new patterns as HA evolves
   - Keep aligned with ABB integration updates

2. **Community Feedback**
   - Monitor GitHub issues for this release
   - Pay attention to sensor availability reports
   - Check for edge cases not covered in testing

3. **Long-term Testing**
   - Monitor stability over weeks/months
   - Check for memory leaks
   - Verify day/night transitions

---

## Lessons Learned

### What Worked Well

1. **Reference Implementation Approach**
   - Having ABB v4.1.5 as a template was invaluable
   - Saved time and reduced risk
   - Benefited from battle-tested solutions

2. **Phased Implementation**
   - Tackling critical fixes first was right priority
   - Breaking work into phases made it manageable
   - Each phase had clear success criteria

3. **Comprehensive Analysis**
   - Deep dive into both codebases paid off
   - Understanding *why* fixes were needed was crucial
   - Comparative analysis revealed non-obvious issues

4. **Tool Usage**
   - Right mix of Read, WebFetch, Edit tools
   - Ruff integration caught issues early
   - Git integration made tracking easy

### What Could Be Improved

1. **Testing Infrastructure**
   - Would benefit from unit tests
   - Mock telnet server for testing
   - Automated regression tests

2. **Documentation**
   - Inline code documentation could be better
   - Protocol documentation would help future developers
   - More examples in config flow

3. **Incremental Releases**
   - Could have released in smaller chunks
   - Multiple betas like ABB v4.1.5
   - More opportunities for user feedback

---

## Conclusion

This release demonstrates how AI-assisted development can:

- **Accelerate Development:** What might take days of analysis was done in hours
- **Improve Quality:** Systematic comparison found issues that might be missed
- **Transfer Knowledge:** Patterns from one integration applied to another
- **Maintain Consistency:** Kept both integrations aligned in style and approach
- **Enhance Documentation:** Comprehensive notes for future reference

### Success Metrics

- ✅ All critical bugs fixed
- ✅ 100% ruff compliance
- ✅ Comprehensive type hints added
- ✅ No breaking changes
- ✅ Full documentation created
- ✅ Beta release for safe testing

### Next Steps

1. **Release v0.2.0-beta.1** to GitHub
2. **Announce** in Home Assistant community forum
3. **Collect feedback** from beta testers
4. **Monitor** for issues and edge cases
5. **Iterate** based on feedback
6. **Release v0.2.0** stable when validated

---

## Acknowledgments

### Development Team

- **@alexdelprete** - Integration author, provided direction and context
- **Claude AI (Sonnet 4.5)** - Code analysis, implementation, and documentation
- **Claude Code** - VSCode extension for seamless integration

### Inspiration & Reference

- **ABB Power-One PVI SunSpec v4.1.5** - Reference implementation for fixes and patterns
- **Home Assistant Core Team** - For excellent integration patterns and documentation
- **Davide Vertuani** - Original Elios4you protocol reverse engineering

### Community

- **Home Assistant Community** - For feedback on integrations
- **HACS** - For making custom integrations accessible
- **Beta Testers** - Who will help validate this release

---

## Transparency Statement

This release was developed with significant assistance from Claude AI (Anthropic's Sonnet 4.5 model) via the Claude Code VSCode extension. All code changes were:

- Analyzed and reviewed by human developer (@alexdelprete)
- Based on proven patterns from existing working code
- Tested with automated linting tools
- Documented comprehensively for future reference
- Released as beta for community validation

The AI acted as a development assistant, not an autonomous developer. Human oversight and judgment guided all decisions.

---

## Contact & Support

- **GitHub Repository:** https://github.com/alexdelprete/ha-4noks-elios4you
- **Issues:** https://github.com/alexdelprete/ha-4noks-elios4you/issues
- **Community Forum:** https://community.home-assistant.io/t/custom-component-4-noks-elios4you-data-integration/692883
- **Developer:** @alexdelprete

---

**Document Version:** 1.0
**Last Updated:** October 12, 2025
**For Release:** v0.2.0-beta.1
