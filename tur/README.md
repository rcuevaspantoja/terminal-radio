# Termux User Repository (TUR) packaging

Recipe for distributing Terminal Radio as a `.deb` on Android Termux:

```bash
pkg install tur-repo   # if needed
pkg install terminal-radio
radio
```

## Maintainer workflow

1. Tag a release on GitHub (`v0.1.0` must match `TERMUX_PKG_VERSION` in `terminal-radio/build.sh`).
2. Update `TERMUX_PKG_SHA256` with `sha256sum` of the release tarball.
3. Open a PR to [termux-user-repository/tur](https://github.com/termux-user-repository/tur) copying `tur/terminal-radio/` into that repo’s `tur/terminal-radio/`.
4. Build locally following [TUR’s setup guide](https://github.com/termux-user-repository/tur#setup-build-environment).

## Until the package is published

Users install from a git checkout:

```bash
python scripts/install-termux.py
```

That script installs Python dependencies and registers `radio` with `PYTHONPATH` pointing at the repo (no `pip install .`).
