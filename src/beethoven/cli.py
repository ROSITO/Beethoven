"""Command line interface for Beethoven."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from beethoven.desktop_server import serve_desktop
from beethoven.core import Score
from beethoven.desktop_state import DesktopSessionStore
from beethoven.packaging import write_sidecar_script
from beethoven.runtime import list_skills, list_soloists, run_objective, score_objective
from beethoven.serialization import context_to_dict, score_to_dict
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

    skills = subparsers.add_parser("skills", help="Inspect orchestration skills.")
    skills_subparsers = skills.add_subparsers(dest="skills_command", required=True)
    skills_list = skills_subparsers.add_parser("list", help="List skills and compatible soloists.")
    skills_list.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "score":
        objective = " ".join(args.objective)
        generated_score = score_objective(objective)
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
        )
        if args.json:
            print(json.dumps(context_to_dict(context), indent=2, ensure_ascii=False))
        else:
            print_run(context_to_dict(context))
        return 0

    if args.command == "desktop":
        serve_desktop(host=args.host, port=args.port, open_browser=args.open)
        return 0

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
        soloists = list_soloists()
        if args.soloists_command == "list":
            if args.json:
                print(json.dumps({"soloists": soloists}, indent=2, ensure_ascii=False))
            else:
                print_soloists(soloists)
            return 0

    if args.command == "skills":
        skills = list_skills()
        if args.skills_command == "list":
            if args.json:
                print(json.dumps({"skills": skills}, indent=2, ensure_ascii=False))
            else:
                print_skills(skills)
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

    parser.print_help(sys.stderr)
    return 2


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
            f"effort={metadata.get('effort')}"
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
