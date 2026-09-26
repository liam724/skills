#!/usr/bin/env python3
"""Extract full human prompts; share local JSONL readers with inspect_failures.

stdout: private JSONL digests. stderr: coverage and errors.
Exit 0: selected sources read successfully; 1: partial coverage;
2: no usable sessions or invalid arguments. No network or write operations.
"""

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


SOURCES = ("claude", "cursor", "codex")
TEXT_TYPES = ("text", "input_text", "output_text")


def arguments(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--sources", default="claude,cursor,codex",
                        help="Comma-separated claude,cursor,codex; default: all")
    window = parser.add_mutually_exclusive_group()
    window.add_argument("--since-days", type=float, default=30,
                        help="Select sessions active in this period (default: 30)")
    window.add_argument("--all", action="store_true", help="Select all history")
    claude_home = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    parser.add_argument("--claude-root", "--root", type=Path,
                        default=claude_home / "projects", help="Claude projects directory")
    parser.add_argument("--cursor-root", type=Path,
                        default=Path.home() / ".cursor/projects",
                        help="Cursor projects directory")
    parser.add_argument("--codex-root", type=Path, default=codex_home,
                        help="Codex home containing sessions/ and archived_sessions/")
    parser.add_argument("--session", type=Path,
                        help="Read one exact path; requires one --sources value")
    args = parser.parse_args()
    args.sources = list(dict.fromkeys(s.strip() for s in args.sources.split(",")))
    if any(s not in SOURCES for s in args.sources):
        parser.error("--sources must contain claude,cursor,codex names")
    if not math.isfinite(args.since_days) or args.since_days <= 0:
        parser.error("--since-days must be a finite positive number")
    if args.session and len(args.sources) != 1:
        parser.error("--session requires exactly one --sources value")
    return args


def diagnostic(message):
    print(message, file=sys.stderr)


def text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block["text"] for block in content
            if isinstance(block, dict) and block.get("type") in TEXT_TYPES
            and isinstance(block.get("text"), str)
        )
    return ""


def human_prompt(record, source):
    if record.get("isMeta") or record.get("isSidechain"):
        return ""
    if source == "codex":
        payload = record.get("payload")
        if not isinstance(payload, dict):
            return ""
        if (record.get("type") == "event_msg"
                and payload.get("type") == "user_message"):
            raw = text(payload.get("message"))
        elif (record.get("type") == "response_item"
              and payload.get("type") == "message"
              and payload.get("role") == "user"):
            raw = text(payload.get("content"))
        else:
            return ""
    else:
        message = record.get("message", record)
        if not isinstance(message, dict):
            return ""
        role = message.get("role") or record.get("role") or record.get("type")
        if role != "user":
            return ""
        raw = text(message.get("content"))
    match = re.search(r"<user_query>(.*?)</user_query>", raw, re.S)
    if match:
        raw = match.group(1)
    raw = re.sub(r"<in-app-browser-context>.*?</in-app-browser-context>",
                 "", raw, flags=re.S | re.I)
    for tag in ("environment_context", "permissions instructions"):
        raw = re.sub(r"<" + tag + r">.*?</" + tag + r">", "", raw, flags=re.S)
    # Known standalone Codex scaffolding, not a human task.
    if raw.lstrip().startswith(("# AGENTS.md instructions for ",
                               "<environment_context>", "<permissions instructions>")):
        return ""
    return raw.strip()


def session_prompts(records, source):
    prompts = []
    previous_kind = None
    for item in records:
        record = item["record"]
        prompt = human_prompt(record, source)
        if prompt:
            kind = record.get("type")
            # Codex often records the same user turn twice. Pair adjacent human
            # representations, rather than discard all response_item messages
            # whenever any event_msg exists in a mixed-format session.
            if (source == "codex" and prompts
                    and previous_kind in ("response_item", "event_msg")
                    and kind != previous_kind and prompts[-1]["text"] == prompt):
                previous_kind = None
                continue
            prompts.append({"line": item["line"], "text": prompt})
            previous_kind = kind
        elif source == "codex":
            payload = record.get("payload")
            if isinstance(payload, dict) and (
                record.get("type") == "response_item" and payload.get("role") != "user"
                or payload.get("type") in ("agent_message", "task_complete", "turn_aborted")
            ):
                previous_kind = None
    return prompts


def is_subagent(records):
    for item in records:
        record = item["record"]
        if record.get("type") != "session_meta":
            continue
        payload = record.get("payload")
        if isinstance(payload, dict):
            origin = payload.get("source")
            if payload.get("thread_source") == "subagent":
                return True
            if isinstance(origin, dict) and "subagent" in origin:
                return True
    return False


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo else None
    except (ValueError, OverflowError, OSError):
        return None


def walk_error(error):
    raise error


def discover(root, source):
    roots = [root / "sessions", root / "archived_sessions"] if source == "codex" else [root]
    found_root = False
    for base in roots:
        try:
            base.stat()
        except FileNotFoundError:
            continue
        if not base.is_dir():
            raise NotADirectoryError(str(base))
        found_root = True
        for directory, dirs, files in os.walk(base, followlinks=False, onerror=walk_error):
            dirs[:] = sorted(d for d in dirs if d != "subagents")
            parent = Path(directory)
            if source == "cursor" and "agent-transcripts" not in parent.parts:
                continue
            for name in sorted(files):
                path = parent / name
                if source == "codex" and not name.startswith("rollout-"):
                    continue
                if path.suffix.lower() in (".jsonl", ".json", ".txt"):
                    yield path
    if not found_root:
        raise FileNotFoundError("No transcript directory under " + str(root))


def read_records(path):
    if path.is_symlink():
        raise ValueError("Transcript symlink not followed; supply its target explicitly")
    if path.suffix.lower() != ".jsonl":
        raise ValueError("Unsupported transcript format: " + path.suffix)
    records = []
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError("Invalid JSON at line " + str(number)) from error
            if not isinstance(record, dict):
                raise ValueError("Expected object at line " + str(number))
            records.append({"line": number, "record": record})
    return records


def sessions(args, stats):
    cutoff = (float("-inf") if args.all else
              datetime.now(timezone.utc).timestamp() - args.since_days * 86400)
    for source in args.sources:
        counts = dict.fromkeys(("files", "reviewed", "outside_window", "subagents",
                                "errors", "mtime_fallback"), 0)
        stats[source] = counts
        root = getattr(args, source + "_root").expanduser()
        try:
            paths = [args.session.expanduser()] if args.session else discover(root, source)
            for path in paths:
                counts["files"] += 1
                try:
                    records = read_records(path)
                    if not records:
                        raise ValueError("Empty transcript")
                    if is_subagent(records):
                        counts["subagents"] += 1
                        continue
                    times = [timestamp(item["record"].get("timestamp")) for item in records]
                    times = [value for value in times if value is not None]
                    if times:
                        latest = max(times)
                    else:
                        latest = path.stat().st_mtime
                        counts["mtime_fallback"] += 1
                    if latest < cutoff:
                        counts["outside_window"] += 1
                        continue
                    prompts = session_prompts(records, source)
                    if not prompts:
                        raise ValueError("No recognized human prompts: empty, auxiliary, "
                                         "or unsupported session schema")
                    counts["reviewed"] += 1
                    yield {"source": source, "path": str(path.absolute()),
                           "prompts": prompts, "records": records}
                except (OSError, UnicodeError, ValueError, RecursionError) as error:
                    counts["errors"] += 1
                    diagnostic("ERROR [{}] {}: {}".format(source, path, error))
            if counts["files"] == 0:
                counts["errors"] += 1
                diagnostic("ERROR [{}] No transcripts found in {}".format(source, root))
        except OSError as error:
            counts["errors"] += 1
            diagnostic("ERROR [{}] {}".format(source, error))


def finish(stats):
    reviewed = sum(c["reviewed"] for c in stats.values())
    errors = sum(c["errors"] for c in stats.values())
    diagnostic(json.dumps({"coverage": stats}, ensure_ascii=False))
    if not reviewed:
        diagnostic("ERROR: No usable sessions in the selected period. "
                   "Check missing sources, errors, and outside_window counts.")
        return 2
    if errors:
        diagnostic("ERROR: Partial coverage. Review diagnostics before use.")
        return 1
    return 0


def main():
    args = arguments("Extract complete human prompts from local JSONL history.")
    stats = {}
    for session in sessions(args, stats):
        session.pop("records")
        print(json.dumps(session, ensure_ascii=False))
    return finish(stats)


if __name__ == "__main__":
    sys.exit(main())
