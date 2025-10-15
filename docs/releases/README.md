# Release Notes Directory

This directory contains detailed release notes for each version of the 4-noks Elios4you integration.

## Structure

Each release has its own markdown file named with the version number:

- `v0.2.0-beta.1.md` - Beta 1 of version 0.2.0
- `v0.2.0.md` - Stable version 0.2.0 (when released)
- `v0.3.0.md` - Future version 0.3.0
- etc.

## Viewing Release Notes

### For Users

- **Latest release notes:** Check the [CHANGELOG.md](../../CHANGELOG.md) in the root directory
- **Specific version details:** Browse files in this directory
- **GitHub releases:** Visit https://github.com/alexdelprete/ha-4noks-elios4you/releases

### For Developers

When creating a new release:

1. **Update version numbers in THREE places** (CRITICAL):
   - `custom_components/4noks_elios4you/manifest.json` - `"version"` field
   - `custom_components/4noks_elios4you/const.py` - `VERSION` constant (line 13)
   - Git tag (step 6 below)

2. Create a new file in this directory: `vX.Y.Z.md` or `vX.Y.Z-beta.N.md`
3. Use the existing release notes as a template
4. Update [CHANGELOG.md](../../CHANGELOG.md) with a summary
5. Run `ruff check` and `ruff format` to ensure 100% compliance
6. Create a git tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
7. Push changes and tag to GitHub

**Why version numbers must be in sync:**
- `manifest.json` - Used by Home Assistant and HACS
- `const.py` VERSION - Displayed in logs and startup message
- Git tag - Creates GitHub release and marks version control

## Release Note Template

Each release note file should include:

- **Version number** in the title
- **Release date**
- **Beta/Stable status** if applicable
- **What's Changed** summary
- **Critical Bug Fixes** (if any)
- **New Features** (if any)
- **Code Quality Improvements**
- **Breaking Changes** (if any)
- **Upgrade Notes**
- **Known Issues**
- **Acknowledgments**
- **Links** to changelog, issues, and documentation

## Release Notes Best Practices

**IMPORTANT:** Follow these standards when writing release notes:

### Official/Stable Releases (e.g., v0.2.0, v1.0.0)

**Document ALL changes since the LAST STABLE release:**

- Example: v0.2.0 release notes should include EVERYTHING from v0.1.0 → v0.2.0
- Include all bug fixes, features, and improvements from the entire beta cycle
- Provide complete upgrade path for users who skip beta versions
- Ensure users upgrading stable-to-stable see the full picture

**Why?** Many users only install stable releases and need to see all changes at once.

### Beta Releases (e.g., v0.2.0-beta.1, v0.2.0-beta.2)

**Document INCREMENTAL changes from the previous beta:**

- Example: beta.2 release notes only document what changed since beta.1
- Focus on specific improvements and fixes in that iteration
- Help beta testers understand what's new to validate
- Keep notes concise and focused on the delta

**Why?** Beta testers need to know what specifically changed to test targeted improvements.

### Examples

**✅ CORRECT - Stable Release:**
```markdown
# Release v0.2.0

This is the official stable release that includes ALL improvements from the beta cycle.

## What's Changed Since v0.1.0

- Fixed sensor availability (from beta.1)
- Fixed unload error (from beta.2)
- Architecture improvements (from beta.3)
- Updated dependencies (new in v0.2.0)
...
```

**✅ CORRECT - Beta Release:**
```markdown
# Release v0.2.0-beta.2

Hotfix release that addresses integration unload error from beta.1.

## What's Changed Since v0.2.0-beta.1

- Added missing close() method to API class
...
```

**❌ WRONG - Stable Release:**
```markdown
# Release v0.2.0

## What's Changed Since v0.2.0-beta.3

- Updated dependencies
```
*Missing all the beta improvements!*

## Navigation

- [← Back to CHANGELOG](../../CHANGELOG.md)
- [← Back to Repository Root](../../)
