"""Command line interface for Beethoven."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from typing import Sequence

from beethoven.desktop_server import serve_desktop
from beethoven.core import Score
from beethoven.config import BeethovenConfig
from beethoven.desktop_state import DesktopSessionStore
from beethoven.packaging import write_recursivemas_bridge, write_sidecar_script
from beethoven.recursive import DEFAULT_RECURSIVE_STYLE, RECURSIVE_STYLES
from beethoven.runtime import (
    check_orchestrator,
    check_soloist,
    list_skills,
    list_soloists,
    run_objective,
    score_objective,
)
from beethoven.serialization import context_to_dict, score_to_dict
from beethoven.solomlx import (
    solomlx_install,
    solomlx_prepare_orchestrator,
    solomlx_start,
    solomlx_status,
    solomlx_stop,
)
from beethoven.validation import list_validation_profiles
from beethoven.workspace import inspect_workspace, list_workspace_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="beethoven",
        description="Universal orchestration CLI for AI scores, soloists, and traces.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    score = subparsers.add_parser("score", help="Create a baseline score from an objective.")
    score.add_argument("objective", nargs="+", help="Objective to transform into a score.")
    score.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    add_strategy_arguments(score)

    run = subparsers.add_parser("run", help="Run a baseline score with the local echo soloist.")
    run.add_argument("objective", nargs="+", help="Objective to orchestrate.")
    run.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    run.add_argument("--soloist", default="local-echo", help="Soloist/router preference.")
    run.add_argument(
        "--permission",
        default="ask",
        choices=["ask", "auto", "read-only"],
        help="Permission mode for the run.",
    )
    run.add_argument(
        "--effort",
        default="medium",
        choices=["low", "medium", "high"],
        help="Execution effort preference.",
    )
    run.add_argument(
        "--validate",
        action="append",
        default=[],
        help="Validation command to run after orchestration. Can be repeated.",
    )
    run.add_argument(
        "--validation-profile",
        action="append",
        default=[],
        help="Named validation profile to run after orchestration. Can be repeated.",
    )
    add_strategy_arguments(run)

    chat = subparsers.add_parser(
        "chat",
        help="Start the interactive terminal workbench.",
        description="Start a real terminal-first Beethoven session.",
    )
    chat.add_argument("--soloist", default="local-echo", help="Soloist/router preference.")
    chat.add_argument(
        "--permission",
        default="ask",
        choices=["ask", "auto", "read-only"],
        help="Permission mode for interactive runs.",
    )
    chat.add_argument(
        "--effort",
        default="medium",
        choices=["low", "medium", "high"],
        help="Execution effort preference.",
    )
    add_strategy_arguments(chat)

    desktop = subparsers.add_parser(
        "desktop",
        help="Serve the local desktop workbench.",
        description="Serve the local desktop workbench.",
    )
    desktop.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    desktop.add_argument("--port", default=4173, type=int, help="Port to bind.")
    desktop.add_argument("--open", action="store_true", help="Open the workbench in a browser.")

    sessions = subparsers.add_parser("sessions", help="Inspect local desktop session history.")
    session_subparsers = sessions.add_subparsers(dest="sessions_command", required=True)
    sessions_list = session_subparsers.add_parser("list", help="List recent desktop sessions.")
    sessions_list.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    sessions_show = session_subparsers.add_parser("show", help="Show one desktop session.")
    sessions_show.add_argument("session_id", help="Session or score id to inspect.")
    sessions_show.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    soloists = subparsers.add_parser("soloists", help="Inspect configured soloists.")
    soloist_subparsers = soloists.add_subparsers(dest="soloists_command", required=True)
    soloists_list = soloist_subparsers.add_parser("list", help="List available and planned soloists.")
    soloists_list.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    soloists_check = soloist_subparsers.add_parser("check", help="Check one soloist adapter.")
    soloists_check.add_argument("soloist_id", help="Soloist id to check.")
    soloists_check.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    soloists_configure = soloist_subparsers.add_parser("configure", help="Persist soloist adapter config.")
    soloists_configure.add_argument("soloist_id", choices=["recursivemas", "openai-compatible"], help="Soloist id to configure.")
    soloists_configure.add_argument(
        "--command",
        dest="adapter_command",
        help="Command used to launch the adapter.",
    )
    soloists_configure.add_argument("--base-url", help="OpenAI-compatible /v1 base URL.")
    soloists_configure.add_argument("--model", help="OpenAI-compatible model id.")
    soloists_configure.add_argument("--api-key", help="OpenAI-compatible API key.")
    soloists_show = soloist_subparsers.add_parser("show", help="Show persisted soloist config.")
    soloists_show.add_argument("soloist_id", choices=["recursivemas", "openai-compatible"], help="Soloist id to show.")
    soloists_show.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    soloists_clear = soloist_subparsers.add_parser("clear", help="Clear persisted soloist config.")
    soloists_clear.add_argument("soloist_id", choices=["recursivemas", "openai-compatible"], help="Soloist id to clear.")

    orchestrator = subparsers.add_parser(
        "orchestrator",
        help="Inspect Beethoven's hidden local orchestration model.",
    )
    orchestrator_subparsers = orchestrator.add_subparsers(dest="orchestrator_command", required=True)
    orchestrator_status = orchestrator_subparsers.add_parser(
        "status",
        help="Show the local orchestrator provider selected by Beethoven.",
    )
    orchestrator_status.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    solomlx = subparsers.add_parser("solomlx", help="Manage the embedded SoloMLX-server runtime brick.")
    solomlx_subparsers = solomlx.add_subparsers(dest="solomlx_command", required=True)
    solomlx_status_parser = solomlx_subparsers.add_parser("status", help="Show SoloMLX runtime status.")
    solomlx_status_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    solomlx_install_parser = solomlx_subparsers.add_parser(
        "install",
        help="Clone and install SoloMLX-server into Beethoven's local runtime directory.",
    )
    solomlx_install_parser.add_argument("--dir", dest="target_dir", help="Installation directory.")
    solomlx_install_parser.add_argument("--upgrade", action="store_true", help="Pull latest changes first.")
    solomlx_install_parser.add_argument(
        "--without-mlx",
        action="store_true",
        help="Install only the API package, without the MLX inference extra.",
    )
    solomlx_prepare_parser = solomlx_subparsers.add_parser(
        "prepare-orchestrator",
        help="Pull the default Ministral orchestration model into SoloMLX.",
    )
    solomlx_prepare_parser.add_argument("--model", help="Model id to pull.")
    solomlx_prepare_parser.add_argument("--dir", dest="target_dir", help="Installation directory.")
    solomlx_prepare_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    solomlx_start_parser = solomlx_subparsers.add_parser("start", help="Start SoloMLX-server.")
    solomlx_start_parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    solomlx_start_parser.add_argument("--port", default=8080, type=int, help="Port to bind.")
    solomlx_start_parser.add_argument("--dir", dest="target_dir", help="Installation directory.")
    solomlx_start_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    solomlx_stop_parser = solomlx_subparsers.add_parser("stop", help="Stop the managed SoloMLX-server.")
    solomlx_stop_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    skills = subparsers.add_parser("skills", help="Inspect orchestration skills.")
    skills_subparsers = skills.add_subparsers(dest="skills_command", required=True)
    skills_list = skills_subparsers.add_parser("list", help="List skills and compatible soloists.")
    skills_list.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    validation = subparsers.add_parser("validation", help="Inspect validation profiles.")
    validation_subparsers = validation.add_subparsers(dest="validation_command", required=True)
    validation_profiles = validation_subparsers.add_parser("profiles", help="List named validation profiles.")
    validation_profiles.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    workspace = subparsers.add_parser("workspace", help="Inspect current project and Git context.")
    workspace_subparsers = workspace.add_subparsers(dest="workspace_command")
    workspace.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    workspace_files = workspace_subparsers.add_parser("files", help="List attachable workspace files.")
    workspace_files.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    workspace_files.add_argument("--limit", default=80, type=int, help="Maximum files to list.")

    package = subparsers.add_parser("package", help="Prepare desktop packaging assets.")
    package_subparsers = package.add_subparsers(dest="package_command", required=True)
    sidecar = package_subparsers.add_parser("sidecar", help="Write a desktop runtime sidecar launcher.")
    sidecar.add_argument(
        "--output",
        default="src-tauri/bin/beethoven-sidecar",
        help="Path for the generated sidecar launcher.",
    )
    recursivemas_bridge = package_subparsers.add_parser(
        "recursivemas-bridge",
        help="Write a RecursiveMAS JSON sidecar bridge.",
    )
    recursivemas_bridge.add_argument(
        "--output",
        default="bridges/recursivemas_beethoven_bridge.py",
        help="Path for the generated RecursiveMAS bridge.",
    )

    return parser


def add_strategy_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--strategy",
        default="baseline",
        choices=["baseline", "recursive"],
        help="Score strategy to use.",
    )
    parser.add_argument(
        "--recursive-style",
        default=DEFAULT_RECURSIVE_STYLE,
        choices=list(RECURSIVE_STYLES),
        help="Recursive collaboration pattern.",
    )
    parser.add_argument(
        "--recursive-rounds",
        default=2,
        type=int,
        help="Recursive rounds to include in the score.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "score":
        objective = " ".join(args.objective)
        generated_score = score_objective(
            objective,
            strategy=args.strategy,
            recursive_style=args.recursive_style,
            recursive_rounds=args.recursive_rounds,
        )
        if args.json:
            print(json.dumps(score_to_dict(generated_score), indent=2, ensure_ascii=False))
        else:
            print_score(generated_score)
        return 0

    if args.command == "run":
        objective = " ".join(args.objective)
        context = run_objective(
            objective,
            soloist=args.soloist,
            permission_mode=args.permission,
            effort=args.effort,
            strategy=args.strategy,
            recursive_style=args.recursive_style,
            recursive_rounds=args.recursive_rounds,
            validation_commands=args.validate,
            validation_profiles=args.validation_profile,
        )
        if args.json:
            print(json.dumps(context_to_dict(context), indent=2, ensure_ascii=False))
        else:
            print_run(context_to_dict(context))
        return 0

    if args.command == "desktop":
        serve_desktop(host=args.host, port=args.port, open_browser=args.open)
        return 0

    if args.command == "chat":
        return run_terminal_session(
            soloist=args.soloist,
            permission_mode=args.permission,
            effort=args.effort,
            strategy=args.strategy,
            recursive_style=args.recursive_style,
            recursive_rounds=args.recursive_rounds,
        )

    if args.command == "sessions":
        store = DesktopSessionStore()
        sessions = store.list_sessions()
        if args.sessions_command == "list":
            if args.json:
                print(json.dumps({"sessions": sessions}, indent=2, ensure_ascii=False))
            else:
                print_sessions(sessions)
            return 0
        if args.sessions_command == "show":
            session = store.get_session(args.session_id)
            if session is None:
                print(f"Session not found: {args.session_id}", file=sys.stderr)
                return 1
            if args.json:
                print(json.dumps({"session": session}, indent=2, ensure_ascii=False))
            else:
                print_session(session)
            return 0

    if args.command == "soloists":
        if args.soloists_command == "list":
            soloists = list_soloists()
            if args.json:
                print(json.dumps({"soloists": soloists}, indent=2, ensure_ascii=False))
            else:
                print_soloists(soloists)
            return 0
        if args.soloists_command == "check":
            report = check_soloist(args.soloist_id)
            if args.json:
                print(json.dumps({"check": report}, indent=2, ensure_ascii=False))
            else:
                print_soloist_check(report)
            return 0 if report.get("available") else 1
        if args.soloists_command == "configure":
            if args.soloist_id == "recursivemas":
                if not args.adapter_command:
                    print("--command is required for recursivemas", file=sys.stderr)
                    return 2
                config_path = BeethovenConfig().set_recursivemas_command(args.adapter_command)
            else:
                if not args.base_url:
                    print("--base-url is required for openai-compatible", file=sys.stderr)
                    return 2
                config_path = BeethovenConfig().set_openai_compatible(
                    base_url=args.base_url,
                    model=args.model or "",
                    api_key=args.api_key or "",
                )
            print(f"Configured {args.soloist_id} in {config_path}")
            return 0
        if args.soloists_command == "show":
            payload = soloist_config_payload(args.soloist_id)
            if args.json:
                print(json.dumps({"soloist": payload}, indent=2, ensure_ascii=False))
            else:
                print(f"Soloist config: {args.soloist_id}")
                print(f"Configured: {payload['configured']}")
                if payload.get("command"):
                    print(f"Command: {payload['command']}")
                if payload.get("base_url"):
                    print(f"Base URL: {payload['base_url']}")
                if payload.get("model"):
                    print(f"Model: {payload['model']}")
                if payload.get("api_key_configured"):
                    print("API key: configured")
            return 0
        if args.soloists_command == "clear":
            if args.soloist_id == "recursivemas":
                config_path = BeethovenConfig().clear_recursivemas_command()
            else:
                config_path = BeethovenConfig().clear_openai_compatible()
            print(f"Cleared {args.soloist_id} config in {config_path}")
            return 0

    if args.command == "orchestrator":
        if args.orchestrator_command == "status":
            report = check_orchestrator()
            if args.json:
                print(json.dumps({"orchestrator": report}, indent=2, ensure_ascii=False))
            else:
                print_orchestrator_status(report)
            return 0 if report.get("available") else 1

    if args.command == "solomlx":
        if args.solomlx_command == "status":
            report = solomlx_status()
            if args.json:
                print(json.dumps({"solomlx": report}, indent=2, ensure_ascii=False))
            else:
                print_solomlx_status(report)
            return 0 if report.get("available") else 1
        if args.solomlx_command == "install":
            report = solomlx_install(
                target_dir=args.target_dir,
                upgrade=args.upgrade,
                with_mlx=not args.without_mlx,
            )
            print(f"SoloMLX installed in {report['path']}")
            print(f"Python: {report['python']}")
            return 0
        if args.solomlx_command == "prepare-orchestrator":
            kwargs = {"target_dir": args.target_dir}
            if args.model:
                kwargs["model"] = args.model
            report = solomlx_prepare_orchestrator(**kwargs)
            if args.json:
                print(json.dumps({"solomlx": report}, indent=2, ensure_ascii=False))
            else:
                print(f"SoloMLX orchestrator model prepared: {report['model']}")
                if report.get("output"):
                    print(report["output"])
            return 0
        if args.solomlx_command == "start":
            report = solomlx_start(host=args.host, port=args.port, target_dir=args.target_dir)
            if args.json:
                print(json.dumps({"solomlx": report}, indent=2, ensure_ascii=False))
            else:
                print_solomlx_status(report)
            return 0
        if args.solomlx_command == "stop":
            report = solomlx_stop()
            if args.json:
                print(json.dumps({"solomlx": report}, indent=2, ensure_ascii=False))
            else:
                print(f"SoloMLX: {report.get('message')}")
            return 0

    if args.command == "skills":
        skills = list_skills()
        if args.skills_command == "list":
            if args.json:
                print(json.dumps({"skills": skills}, indent=2, ensure_ascii=False))
            else:
                print_skills(skills)
            return 0

    if args.command == "validation":
        profiles = list_validation_profiles()
        if args.validation_command == "profiles":
            if args.json:
                print(json.dumps({"profiles": profiles}, indent=2, ensure_ascii=False))
            else:
                print_validation_profiles(profiles)
            return 0

    if args.command == "workspace":
        if args.workspace_command == "files":
            workspace_files = list_workspace_files(limit=args.limit)
            if args.json:
                print(json.dumps(workspace_files, indent=2, ensure_ascii=False))
            else:
                print_workspace_files(workspace_files)
            return 0
        workspace = inspect_workspace()
        if args.json:
            print(json.dumps({"workspace": workspace}, indent=2, ensure_ascii=False))
        else:
            print_workspace(workspace)
        return 0

    if args.command == "package":
        if args.package_command == "sidecar":
            output_path = write_sidecar_script(args.output)
            print(f"Sidecar launcher written to {output_path}")
            return 0
        if args.package_command == "recursivemas-bridge":
            output_path = write_recursivemas_bridge(args.output)
            print(f"RecursiveMAS bridge written to {output_path}")
            print(f'export BEETHOVEN_RECURSIVEMAS_COMMAND="{sys.executable} {output_path}"')
            return 0

    parser.print_help(sys.stderr)
    return 2


def run_terminal_session(
    *,
    soloist: str = "local-echo",
    permission_mode: str = "ask",
    effort: str = "medium",
    strategy: str = "baseline",
    recursive_style: str = DEFAULT_RECURSIVE_STYLE,
    recursive_rounds: int = 2,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    """Run the terminal-first Beethoven loop."""
    controls = {
        "soloist": soloist,
        "permission_mode": permission_mode,
        "effort": effort,
        "strategy": strategy,
        "recursive_style": recursive_style,
        "recursive_rounds": str(recursive_rounds),
        "validation_profile": "none",
    }
    output_fn("Beethoven terminal workbench")
    output_fn("Type an objective to run it, or /help for commands.")
    output_fn("")
    print_terminal_controls(controls, output_fn)

    while True:
        try:
            raw_value = input_fn("beethoven> ")
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            output_fn("Session closed.")
            return 0

        value = raw_value.strip()
        if not value:
            continue
        if value in {"/exit", "/quit"}:
            output_fn("Session closed.")
            return 0
        if value.startswith("/"):
            handle_terminal_command(value, controls, output_fn)
            continue
        run_terminal_objective(value, controls, output_fn)


def handle_terminal_command(
    value: str,
    controls: dict[str, str],
    output_fn: Callable[[str], None],
) -> None:
    command, _, argument = value.partition(" ")
    argument = argument.strip()

    if command == "/help":
        print_terminal_help(output_fn)
        return
    if command == "/controls":
        print_terminal_controls(controls, output_fn)
        return
    if command == "/score":
        if not argument:
            output_fn("Usage: /score <objective>")
            return
        print_score(
            score_objective(
                argument,
                strategy=controls["strategy"],
                recursive_style=controls["recursive_style"],
                recursive_rounds=int(controls["recursive_rounds"]),
            )
        )
        return
    if command == "/run":
        if not argument:
            output_fn("Usage: /run <objective>")
            return
        run_terminal_objective(argument, controls, output_fn)
        return
    if command == "/sessions":
        print_sessions(DesktopSessionStore().list_sessions())
        return
    if command == "/soloists":
        print_soloists(list_soloists())
        return
    if command == "/orchestrator":
        print_orchestrator_status(check_orchestrator())
        return
    if command == "/solomlx":
        print_solomlx_status(solomlx_status())
        return
    if command == "/skills":
        print_skills(list_skills())
        return
    if command == "/validation-profiles":
        print_validation_profiles(list_validation_profiles())
        return
    if command == "/workspace":
        print_workspace(inspect_workspace())
        return
    if command == "/files":
        files_payload = list_workspace_files(limit=40)
        if argument:
            files_payload = {
                **files_payload,
                "files": [
                    item
                    for item in files_payload["files"]
                    if argument.lower() in str(item.get("path", "")).lower()
                ],
            }
        print_workspace_files(files_payload)
        return
    if command == "/permission":
        set_terminal_control("permission_mode", argument, {"ask", "auto", "read-only"}, controls, output_fn)
        return
    if command == "/effort":
        set_terminal_control("effort", argument, {"low", "medium", "high"}, controls, output_fn)
        return
    if command == "/strategy":
        set_terminal_control("strategy", argument, {"baseline", "recursive"}, controls, output_fn)
        return
    if command == "/recursive-style":
        set_terminal_control("recursive_style", argument, set(RECURSIVE_STYLES), controls, output_fn)
        return
    if command == "/recursive-rounds":
        if not argument:
            output_fn(f"recursive_rounds={controls['recursive_rounds']}")
            return
        try:
            rounds = int(argument)
        except ValueError:
            output_fn("Invalid recursive_rounds. Expected an integer.")
            return
        controls["recursive_rounds"] = str(rounds)
        output_fn(f"recursive_rounds={rounds}")
        return
    if command == "/validation-profile":
        allowed_profiles = {str(profile["id"]) for profile in list_validation_profiles()}
        set_terminal_control("validation_profile", argument, {"none", *allowed_profiles}, controls, output_fn)
        return
    if command == "/soloist":
        if not argument:
            output_fn(f"soloist={controls['soloist']}")
            return
        controls["soloist"] = argument
        output_fn(f"soloist={argument}")
        return

    output_fn(f"Unknown command: {command}. Type /help.")


def run_terminal_objective(
    objective: str,
    controls: dict[str, str],
    output_fn: Callable[[str], None],
) -> None:
    output_fn("")
    output_fn(f"Objective: {objective}")
    context = run_objective(
        objective,
        soloist=controls["soloist"],
        permission_mode=controls["permission_mode"],
        effort=controls["effort"],
        strategy=controls["strategy"],
        recursive_style=controls["recursive_style"],
        recursive_rounds=int(controls["recursive_rounds"]),
        validation_profiles=[] if controls["validation_profile"] == "none" else [controls["validation_profile"]],
    )
    print_run(context_to_dict(context))
    output_fn("")


def set_terminal_control(
    key: str,
    value: str,
    allowed: set[str],
    controls: dict[str, str],
    output_fn: Callable[[str], None],
) -> None:
    if not value:
        output_fn(f"{key}={controls[key]}")
        return
    if value not in allowed:
        formatted = ", ".join(sorted(allowed))
        output_fn(f"Invalid {key}. Expected one of: {formatted}")
        return
    controls[key] = value
    output_fn(f"{key}={value}")


def print_terminal_controls(controls: dict[str, str], output_fn: Callable[[str], None]) -> None:
    output_fn(
        "Controls: "
        f"soloist={controls['soloist']} · "
        f"permission={controls['permission_mode']} · "
        f"effort={controls['effort']} · "
        f"strategy={controls['strategy']} · "
        f"recursive={controls['recursive_style']}/{controls['recursive_rounds']} · "
        f"validation={controls['validation_profile']}"
    )


def print_terminal_help(output_fn: Callable[[str], None]) -> None:
    output_fn("Commands:")
    output_fn("- /run <objective>       Run an objective")
    output_fn("- /score <objective>     Preview a score")
    output_fn("- /sessions              List local sessions")
    output_fn("- /soloists              List soloists")
    output_fn("- /orchestrator          Show hidden local orchestrator status")
    output_fn("- /solomlx               Show embedded SoloMLX runtime status")
    output_fn("- /skills                List orchestration skills")
    output_fn("- /validation-profiles   List named validation profiles")
    output_fn("- /workspace             Show workspace/Git context")
    output_fn("- /files [query]         List attachable files")
    output_fn("- /permission <mode>     ask, auto, read-only")
    output_fn("- /effort <level>        low, medium, high")
    output_fn("- /soloist <id>          Set soloist")
    output_fn("- /strategy <mode>       baseline, recursive")
    output_fn("- /recursive-style <s>   sequential, deliberation, mixture, distillation")
    output_fn("- /recursive-rounds <n>  Set recursive rounds")
    output_fn("- /validation-profile <p> none, desktop, lint, tests, full")
    output_fn("- /controls              Show current controls")
    output_fn("- /exit                  Close the terminal session")


def print_score(score: Score) -> None:
    data = score_to_dict(score)
    print(f"Score: {data['id']}")
    print(f"Objective: {data['objective']}")
    print()
    for task in data["tasks"]:
        dependencies = ", ".join(task["depends_on"]) or "none"
        print(f"- {task['id']} [{task['capability']}]")
        print(f"  depends_on: {dependencies}")
        print(f"  instruction: {task['instruction']}")


def print_run(data: dict[str, object]) -> None:
    score = data["score"]
    assert isinstance(score, dict)
    print(f"Beethoven performed {score['id']}")
    print(f"Objective: {score['objective']}")
    metadata = score.get("metadata", {})
    assert isinstance(metadata, dict)
    if metadata:
        print(
            "Controls: "
            f"soloist={metadata.get('soloist')} · "
            f"permission={metadata.get('permission_mode')} · "
            f"effort={metadata.get('effort')} · "
            f"strategy={metadata.get('strategy', 'baseline')}"
        )
    print()
    print("Trace")
    for event in data["trace"]:
        print(f"- {event}")
    print()
    print("Statuses")
    statuses = data["statuses"]
    assert isinstance(statuses, dict)
    for task_id, status in statuses.items():
        print(f"- {task_id}: {status}")
    artifacts = data.get("artifacts", {})
    if isinstance(artifacts, dict) and "validation" in artifacts:
        validation = artifacts["validation"]
        if isinstance(validation, dict):
            print()
            print("Validation")
            for result in validation.get("output", []):
                if not isinstance(result, dict):
                    continue
                marker = "passed" if result.get("passed") else "failed"
                print(f"- {result.get('command')}: {marker}")


def print_sessions(sessions: list[dict[str, object]]) -> None:
    if not sessions:
        print("No desktop sessions yet.")
        return

    for session in sessions:
        title = session.get("title", "Untitled score")
        score_id = session.get("score_id", session.get("id", "unknown"))
        project = session.get("project", "Beethoven")
        branch = session.get("branch", "main")
        status = session.get("status", "unknown")
        print(f"- {title} [{status}]")
        print(f"  score: {score_id} · project: {project} · branch: {branch}")


def soloist_config_payload(soloist_id: str) -> dict[str, object]:
    config = BeethovenConfig()
    if soloist_id == "recursivemas":
        command = config.get_recursivemas_command()
        return {
            "id": soloist_id,
            "command": command,
            "configured": bool(command),
        }
    openai_config = config.get_openai_compatible()
    return {
        "id": soloist_id,
        "base_url": openai_config.get("base_url", ""),
        "model": openai_config.get("model", ""),
        "api_key_configured": bool(openai_config.get("api_key", "")),
        "configured": bool(openai_config.get("base_url", "")),
    }


def print_session(session: dict[str, object]) -> None:
    print(f"Session: {session.get('title', 'Untitled score')}")
    print(f"Score: {session.get('score_id', session.get('id', 'unknown'))}")
    print(f"Objective: {session.get('objective', '')}")
    print(
        "Controls: "
        f"soloist={session.get('soloist')} · "
        f"permission={session.get('permission_mode')} · "
        f"effort={session.get('effort')}"
    )
    print("Trace")
    for event in session.get("trace", []):
        print(f"- {event}")


def print_soloists(soloists: list[dict[str, object]]) -> None:
    for soloist in soloists:
        capabilities = ", ".join(str(item) for item in soloist.get("capabilities", []))
        print(f"- {soloist.get('name')} [{soloist.get('status')}]")
        print(
            f"  id: {soloist.get('id')} · provider: {soloist.get('provider')} · "
            f"locality: {soloist.get('locality')}"
        )
        print(f"  capabilities: {capabilities}")


def print_soloist_check(report: dict[str, object]) -> None:
    print(f"Soloist check: {report.get('id')}")
    print(f"Status: {report.get('status')}")
    print(f"Available: {report.get('available')}")
    print(f"Message: {report.get('message')}")
    command = report.get("command")
    if command:
        print(f"Command: {command}")
    output_preview = report.get("output_preview")
    if output_preview:
        print(f"Output: {output_preview}")


def print_orchestrator_status(report: dict[str, object]) -> None:
    print(f"Orchestrator: {report.get('id')}")
    print(f"Status: {report.get('status')}")
    print(f"Available: {report.get('available')}")
    print(f"Provider: {report.get('provider', report.get('configured_provider'))}")
    model = report.get("model")
    if model:
        print(f"Model: {model}")
    base_url = report.get("base_url")
    if base_url:
        print(f"Base URL: {base_url}")
    print(f"Message: {report.get('message')}")


def print_solomlx_status(report: dict[str, object]) -> None:
    print(f"SoloMLX: {report.get('status')}")
    print(f"Installed: {report.get('installed')}")
    print(f"Running: {report.get('process_running')}")
    print(f"Available: {report.get('available')}")
    print(f"Path: {report.get('path')}")
    print(f"Base URL: {report.get('base_url')}")
    models = report.get("models")
    if isinstance(models, list) and models:
        print(f"Models: {', '.join(str(model) for model in models)}")
    print(f"Message: {report.get('message')}")


def print_skills(skills: list[dict[str, object]]) -> None:
    for skill in skills:
        soloists = skill.get("soloists", [])
        assert isinstance(soloists, list)
        available = [
            str(soloist.get("name"))
            for soloist in soloists
            if isinstance(soloist, dict) and soloist.get("status") == "available"
        ]
        planned = [
            str(soloist.get("name"))
            for soloist in soloists
            if isinstance(soloist, dict) and soloist.get("status") != "available"
        ]
        print(f"- {skill.get('name')} [{skill.get('status')}]")
        print(f"  id: {skill.get('id')}")
        if available:
            print(f"  available: {', '.join(available)}")
        if planned:
            print(f"  planned: {', '.join(planned)}")


def print_validation_profiles(profiles: list[dict[str, object]]) -> None:
    for profile in profiles:
        commands = profile.get("commands", [])
        assert isinstance(commands, list)
        print(f"- {profile.get('name')} [{profile.get('id')}]")
        print(f"  {profile.get('description')}")
        for command in commands:
            print(f"  command: {command}")


def print_workspace(workspace: dict[str, object]) -> None:
    print(f"Workspace: {workspace.get('name')}")
    print(f"Path: {workspace.get('path')}")
    if workspace.get("is_git"):
        print(f"Git: {workspace.get('branch')} · changes={workspace.get('changes')}")
    else:
        print("Git: not detected")


def print_workspace_files(payload: dict[str, object]) -> None:
    workspace = payload.get("workspace", {})
    assert isinstance(workspace, dict)
    files = payload.get("files", [])
    assert isinstance(files, list)
    print(f"Workspace files: {workspace.get('name')}")
    if not files:
        print("No attachable files found.")
        return
    for item in files:
        assert isinstance(item, dict)
        print(f"- {item.get('path')}")


if __name__ == "__main__":
    raise SystemExit(main())
