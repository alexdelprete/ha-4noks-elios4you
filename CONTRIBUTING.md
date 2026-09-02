# Contributing

Thanks for wanting to contribute. This document covers the development environment; for what to
change and why, open an issue first so we can agree on the approach.

## Development environment: use the devcontainer

The repository ships a devcontainer, and it is **the supported way to develop and run the tests**
on every platform.

Open the repository in VS Code with the [Dev Containers][devcontainers] extension and choose
*Reopen in Container*. Docker Desktop is enough on Windows and macOS. The container gives you,
with no further setup:

- **Python 3.14** with all development dependencies, installed via `uv pip install -e '.[dev]'`
  from `pyproject.toml`;
- the **`fournoks_elios4you` → `4noks_elios4you` symlink**, created by `postCreateCommand`. It
  exists because `4noks_elios4you` starts with a digit and is therefore not importable from
  Python: the tests import through the symlinked name;
- `pre-commit` installed and wired up;
- a live Home Assistant instance on port **8123** to test against a real setup.

Then:

```bash
python -m pytest tests/          # the whole suite
python -m pytest tests/test_api.py
ruff check custom_components/ tests/
ruff format custom_components/ tests/
```

## ⚠️ The test suite cannot run natively on Windows

This is not a matter of missing packages: `homeassistant/runner.py` imports **`fcntl`**, which is
a Unix-only module, so the import fails before the first test is collected. No amount of
installing fixes it.

Windows contributors have three options, in order of preference: the **devcontainer** (above),
**WSL**, or any Linux container.

Four further obstacles are worth knowing about, because each one produces an error message that
points somewhere else. They are all handled by the devcontainer, and are listed here only to
explain why it is the supported path rather than a convenience:

| Symptom | Cause |
|---|---|
| `No matching distribution found for homeassistant>=2026.3.0` | Python older than **3.14.2** — pip does not say so. |
| `No module named 'custom_components.fournoks_elios4you'` | Missing symlink; git on Windows does not recreate it. |
| `Error importing plugin "pytest_homeassistant_custom_component"` | Deliberately absent — see below. |
| `ln: failed to create symbolic link: Not a directory` | An NTFS junction does not survive a Docker bind mount. |

## Installing dependencies by hand

If you are not using the devcontainer, **the order matters** — install
`pytest-homeassistant-custom-component` first, at the exact version pinned in `pyproject.toml`:

```bash
pip install "pytest-homeassistant-custom-component==<version pinned in pyproject.toml>"
pip install -r requirements-dev.txt   # layered on top
```

`pytest-homeassistant-custom-component` is intentionally absent from `requirements-dev.txt`: it
pins an exact `homeassistant` version, while `requirements-dev.txt` asks for a range. Installing
both in a single resolution step makes pip reconcile the two, which is why the packages are
layered instead. The first line of that file says so — it is not an omission.

[devcontainers]: https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers
