# Desktop Packaging

Beethoven now includes a first Tauri v2 desktop shell in `src-tauri/`.

The current desktop target is a development wrapper around the local Beethoven
desktop server:

```bash
pip install -e ".[dev]"
npm install
npm run tauri:dev
```

`npm install` installs `@tauri-apps/cli`. The native shell also requires the
Rust toolchain because Tauri calls `cargo metadata` before launching dev mode.
If `cargo` is missing, `npm run tauri:dev` fails before the Python sidecar starts.
Run Beethoven's packaging doctor to check these prerequisites before launching
Tauri:

```bash
beethoven package doctor
beethoven package doctor --json
```

The desktop runtime panel also calls the same diagnostic through `/api/packaging`.
On the current development machine, npm, the Tauri CLI, sidecar script, and
Tauri config are detected, while Cargo is the blocking prerequisite.

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

The launcher is also versioned at `src-tauri/bin/beethoven-sidecar` and is
listed in `tauri.conf.json` as an external binary. `beforeBuildCommand`
regenerates it before a Tauri build.

Resolution order:

1. `BEETHOVEN_BIN`, when set;
2. `beethoven` on `PATH`;
3. `BEETHOVEN_PYTHON`, when set;
4. local `.venv/bin/python`;
5. `python3` on `PATH`, using `-m beethoven.cli`.

## Python Sidecar Strategy

The desktop app should treat Python as Beethoven's orchestration engine, not as
an implementation detail hidden inside the frontend. The packaging path is:

1. **Development**: Tauri starts `beethoven desktop` with the editable Python
   package installed in the active environment.
2. **Local sidecar launcher**: `beethoven package sidecar` writes a launcher in
   `src-tauri/bin/` that delegates to the installed `beethoven` console script
   or a Python module fallback.
3. **Bundled sidecar**: production builds should ship a hermetic Python runtime
   containing the `beethoven` package and its dependencies, then launch it as a
   Tauri sidecar process.
4. **Health and streaming contract**: the app waits for `/api/health`, sends
   runs to `/api/run/stream`, and consumes newline-delimited run events until a
   final `run_completed` event arrives.
5. **Configuration**: `BEETHOVEN_HOST`, `BEETHOVEN_PORT`, `BEETHOVEN_HOME`,
   `BEETHOVEN_OLLAMA_MODEL`, and `BEETHOVEN_OLLAMA_TIMEOUT` remain the stable
   environment boundary between Tauri and the Python engine.

The sidecar must own local state under `BEETHOVEN_HOME`, expose only localhost
HTTP endpoints, and keep provider credentials or model configuration outside the
frontend bundle.

## Current Scope

This is intentionally the first native-app bridge, not the final installer:

- the desktop UI remains the static workbench in `desktop/`;
- the Python runtime remains the source of truth for orchestration;
- Tauri provides the native window and app shell;
- `beethoven package doctor` is the single non-destructive health check for the
  local packaging toolchain;
- production bundling needs the bundled sidecar phase above before installers
  are considered complete.

## Next Packaging Steps

1. Replace the shell launcher with a fully bundled Python runtime sidecar.
2. Add app icons and platform bundle metadata.
3. Add CI checks for `beethoven package doctor` and `npm run tauri:dev` smoke
   tests where Rust/Cargo and Tauri are available.
4. Add a startup supervisor that launches the sidecar, waits for health, and
   reports failures inside the desktop UI.
