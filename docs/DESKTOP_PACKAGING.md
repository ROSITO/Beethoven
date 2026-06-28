# Desktop Packaging

Beethoven now includes a first Tauri v2 desktop shell in `src-tauri/`.

The current desktop target is a development wrapper around the local Beethoven
desktop server:

```bash
pip install -e ".[dev]"
npm install
npm run tauri:dev
```

The Tauri window loads `http://127.0.0.1:4173`, and `beforeDevCommand` starts:

```bash
beethoven desktop --host 127.0.0.1 --port 4173
```

## Sidecar Launcher

The first packaging bridge can generate a local sidecar launcher:

```bash
beethoven package sidecar
```

By default this writes:

```bash
src-tauri/bin/beethoven-sidecar
```

The launcher delegates to:

```bash
beethoven desktop --host "$BEETHOVEN_HOST" --port "$BEETHOVEN_PORT"
```

with defaults of `127.0.0.1` and `4173`.

## Current Scope

This is intentionally the first native-app bridge, not the final installer:

- the desktop UI remains the static workbench in `desktop/`;
- the Python runtime remains the source of truth for orchestration;
- Tauri provides the native window and app shell;
- production bundling will need a Python sidecar or a dedicated backend process
  strategy before installers are considered complete.

## Next Packaging Steps

1. Replace the shell launcher with a fully bundled Python runtime sidecar.
2. Add app icons and platform bundle metadata.
3. Add CI checks for `npm run tauri:dev` smoke tests where Tauri is available.
4. Decide whether production builds load `frontendDist` directly or always start
   a local backend sidecar.
