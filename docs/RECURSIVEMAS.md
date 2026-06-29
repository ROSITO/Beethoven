# RecursiveMAS Integration

Beethoven integrates RecursiveMAS in two layers:

1. Native recursive scores, always available through `--strategy recursive`.
2. An optional `recursivemas` soloist adapter backed by a local sidecar command.

The native strategy keeps recursive work visible as regular Beethoven `Task`
objects. The sidecar adapter lets a RecursiveMAS runtime execute those tasks
without forcing RecursiveMAS dependencies into the default Beethoven install.

## Native Recursive Scores

```bash
beethoven score "Integrate RecursiveMAS" \
  --strategy recursive \
  --recursive-style deliberation \
  --recursive-rounds 2
```

Supported styles:

- `sequential`
- `deliberation`
- `mixture`
- `distillation`

## Sidecar Activation

Set `BEETHOVEN_RECURSIVEMAS_COMMAND` to a command that reads one JSON payload
from stdin and writes either JSON or plain text to stdout.

```bash
beethoven package recursivemas-bridge --output bridges/recursivemas_beethoven_bridge.py
export BEETHOVEN_RECURSIVEMAS_COMMAND="python3 /path/to/recursivemas_beethoven_bridge.py"

beethoven run "Solve with RecursiveMAS" \
  --soloist recursivemas \
  --strategy recursive \
  --recursive-style deliberation \
  --recursive-rounds 2
```

When the command is configured and executable, `beethoven soloists list` reports
`RecursiveMAS [available]`. Otherwise it remains `planned`.

You can also persist the command under `BEETHOVEN_HOME/config.json` so the
desktop and future shells can reuse it without an environment export:

```bash
beethoven soloists configure recursivemas \
  --command "python3 /path/to/recursivemas_beethoven_bridge.py"
beethoven soloists show recursivemas
beethoven soloists clear recursivemas
```

`BEETHOVEN_RECURSIVEMAS_COMMAND` still takes priority over the persisted config
when both are present.

Use the healthcheck when wiring a local bridge:

```bash
beethoven soloists check recursivemas
beethoven soloists check recursivemas --json
```

The desktop API exposes the same diagnostic:

```bash
curl http://127.0.0.1:4173/api/soloists/recursivemas/check
```

The desktop API can also read, save, and clear the persisted command:

```bash
curl http://127.0.0.1:4173/api/soloists/recursivemas/config
curl -X POST http://127.0.0.1:4173/api/soloists/recursivemas/config \
  -H "Content-Type: application/json" \
  -d '{"command":"python3 /path/to/recursivemas_beethoven_bridge.py"}'
curl -X DELETE http://127.0.0.1:4173/api/soloists/recursivemas/config
```

In the desktop workbench, open `Skills`, paste the bridge command, save it, then
run `Check RecursiveMAS`.

## Input Protocol

Beethoven sends this JSON shape to the sidecar:

```json
{
  "protocol": "beethoven.recursivemas.v1",
  "task": {
    "id": "propose_round_1",
    "instruction": "Propose solution round 1 from the current state.",
    "capability": "plan",
    "depends_on": ["frame_problem"],
    "metadata": {
      "recursive_role": "proposer",
      "round": 1
    }
  },
  "score": {
    "id": "score-recursive-...",
    "objective": "User objective",
    "metadata": {
      "strategy": "recursive",
      "recursive_style": "deliberation",
      "recursive_rounds": 2
    },
    "tasks": []
  },
  "artifacts": {
    "frame_problem": {
      "output": "previous output",
      "metadata": {},
      "cost": 0.0,
      "tokens": 0
    }
  }
}
```

## Output Protocol

The sidecar may write plain text. Beethoven stores it as the task output.

For richer results, write JSON:

```json
{
  "output": "task result",
  "metadata": {
    "backend": "recursive-mas",
    "model": "your-model"
  },
  "tokens": 123,
  "cost": 0.0
}
```

## Minimal Bridge

Beethoven can generate this bridge for you:

```bash
beethoven package recursivemas-bridge
```

The generated file contains this shape:

```python
from __future__ import annotations

import json
import sys

payload = json.loads(sys.stdin.read())
task = payload["task"]

# Replace this with RecursiveMAS inference/training/runtime calls.
result = {
    "output": f"RecursiveMAS handled {task['id']} as {task['capability']}",
    "metadata": {"backend": "recursive-mas"},
    "tokens": 0,
    "cost": 0.0,
}

print(json.dumps(result))
```

## Why Sidecar First?

RecursiveMAS has its own environment expectations. Keeping it behind a sidecar
lets Beethoven remain installable and testable while still providing a stable
runtime boundary for the real RecursiveMAS backend.
