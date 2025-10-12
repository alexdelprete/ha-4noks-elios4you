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

1. Create a new file in this directory: `vX.Y.Z.md` or `vX.Y.Z-beta.N.md`
2. Use the existing release notes as a template
3. Update [CHANGELOG.md](../../CHANGELOG.md) with a summary
4. Update the version in `manifest.json`
5. Create a git tag: `git tag vX.Y.Z`

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

## Navigation

- [← Back to CHANGELOG](../../CHANGELOG.md)
- [← Back to Repository Root](../../)
