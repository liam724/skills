#!/usr/bin/env python3
"""Flag possible failures and emit full original session records.

Signals are heuristic, not diagnoses. No model or network calls are used.
--session with one --sources value retrieves any session, even without hits.
Exit codes and source options match extract_prompts.py.
"""

import json
import re
import sys

from extract_prompts import arguments, finish, sessions


CORRECTION = re.compile(
    r"\b(that(?:'s| is) (?:wrong|incorrect|not what)|"
    r"not what I (?:asked|wanted|meant)|you (?:forgot|missed|ignored)|"
    r"still (?:broken|failing|not working)|does(?:n't| not) work|"
    r"try again|stop doing|undo that|revert that)\b", re.I)
ERROR_TEXT = re.compile(
    r"\b(traceback \(most recent call last\)|permission denied|"
    r"command not found|access denied|timed out|rate limit exceeded|"
    r"tests? failed|build failed|fatal error)", re.I)
EXIT_TEXT = re.compile(
    r"\b(?:exit(?:ed)?(?: with)?(?: code)?|exit_code)\s*[:=]?\s*(-?\d+)\b", re.I)
TOOL_OUTPUT_TYPES = ("tool_result", "function_call_output", "custom_tool_call_output")


def walk(value):
    # Iterative traversal also handles deeply nested tool output.
    stack = [value]
    while stack:
        current = stack.pop()
        yield current
        if isinstance(current, dict):
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def tool_outputs(record):
    for value in walk(record):
        if isinstance(value, dict) and (
            value.get("type") in TOOL_OUTPUT_TYPES or value.get("role") == "tool"
        ):
            yield value


def structured_error(output):
    for value in walk(output):
        if not isinstance(value, dict):
            continue
        if value.get("is_error") is True or value.get("isError") is True:
            return True
        if value.get("status") in ("failed", "error", "timed_out"):
            return True
        for key in ("exit_code", "returncode"):
            code = value.get(key)
            if isinstance(code, int) and not isinstance(code, bool) and code != 0:
                return True
    return False


def signals(session):
    matches = []
    for prompt in session["prompts"]:
        if CORRECTION.search(prompt["text"]):
            matches.append({"line": prompt["line"], "signal": "possible_user_correction"})
    for item in session["records"]:
        for output in tool_outputs(item["record"]):
            # Codex and MCP sometimes embed a structured result as a JSON string.
            evidence = [output]
            for key in ("output", "content"):
                encoded = output.get(key)
                if isinstance(encoded, str) and encoded.lstrip().startswith(("{", "[")):
                    try:
                        evidence.append(json.loads(encoded))
                    except (ValueError, RecursionError):
                        pass  # Plain text remains available for heuristic inspection.
            if structured_error(evidence):
                matches.append({"line": item["line"], "signal": "structured_tool_failure"})
                break
            strings = [value for value in walk(evidence) if isinstance(value, str)]
            failed = any(ERROR_TEXT.search(value) for value in strings)
            nonzero = any(match.group(1).lstrip("-0") for value in strings
                          for match in EXIT_TEXT.finditer(value))
            if failed or nonzero:
                matches.append({"line": item["line"], "signal": "possible_tool_failure"})
                break
    return matches


def main():
    args = arguments("Find possible failures and emit full original JSONL records.")
    stats = {}
    candidates = 0
    for session in sessions(args, stats):
        found = signals(session)
        if found or args.session:
            candidates += 1
            print(json.dumps({"source": session["source"], "path": session["path"],
                              "signals": found, "records": session["records"]},
                             ensure_ascii=False))
    print(json.dumps({"emitted_sessions": candidates, "notice":
          "Heuristics are incomplete and text patterns are English. "
          "No matches does not establish success. Full records may contain sensitive data."}),
          file=sys.stderr)
    return finish(stats)


if __name__ == "__main__":
    sys.exit(main())
