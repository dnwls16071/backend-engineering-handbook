#!/usr/bin/env python3
"""Search the Lounge wiki and check its Markdown and evidence locally."""

import argparse
from datetime import date
from difflib import SequenceMatcher
from itertools import islice
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path("wiki/evidence.json")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HEADING = re.compile(r"^ {0,3}#{1,6}(?:\s|$)")
NUMBERED_HEADING = re.compile(r"^ {0,3}##\s+(\d+)\.\s+")
INLINE_CODE = re.compile(r"(`+)(?!`).*?(?<!`)\1(?!`)")
LINK = re.compile(r"(?<!\\)\[[^\[\]\n]*\]\((?:<([^>\n]+)>|([^\s()]+))\)")


def git_paths(*args):
    result = subprocess.run(
        ["git", "--literal-pathspecs", *args], cwd=ROOT, check=True, stdout=subprocess.PIPE
    )
    return {Path(os.fsdecode(name)) for name in result.stdout.split(b"\0") if name}


def within(path, scope):
    return path == scope or scope in path.parents


def in_repo(path):
    return (ROOT / path).resolve().relative_to(ROOT)


def wiki_path(path):
    return not any(part.startswith(".") for part in path.parts)


def get_scope(value):
    try:
        path = in_repo(Path(value))
    except ValueError:
        raise ValueError("Choose a path inside the repository.") from None
    if not wiki_path(path) or not (ROOT / path).exists():
        raise ValueError(f"Wiki path does not exist: {value}")
    return path


def changed_paths(scope, include_untracked=True):
    diff = ("diff", "--no-ext-diff", "--no-renames", "--name-only", "-z")
    paths = git_paths(*diff, "--", str(scope)) | git_paths(*diff, "--cached", "--", str(scope))
    if include_untracked:
        paths |= git_paths("ls-files", "--others", "--exclude-standard", "-z", "--", str(scope))
    return paths


def markdown_paths(scope, changed=False):
    paths = changed_paths(scope) if changed else git_paths(
        "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", str(scope)
    )
    return sorted(
        path for path in paths
        if path.suffix == ".md" and wiki_path(path) and (ROOT / path).is_file()
        and (ROOT / path).resolve() == ROOT / path
    )


def issue(path, line, code, message):
    return {"path": path.as_posix(), "line": line, "code": code, "message": message}


def check_markdown(path, lines, uncovered_lines=()):
    issues = []
    fence = None
    heading = 0
    for number, line in enumerate(lines, 1):
        marker = FENCE.match(line)
        if fence:
            if marker and marker[1].startswith(fence[0]) and not marker[2].strip():
                fence = None
            continue
        if marker and (marker[1][0] == "~" or "`" not in marker[2]):
            fence = (marker[1], number)
            continue
        if number in uncovered_lines and line.strip(" \t|:-") and not HEADING.match(line):
            issues.append(issue(
                path, number, "missing-evidence", "Register the changed line in wiki/evidence.json."
            ))
        match = NUMBERED_HEADING.match(line)
        if match:
            found = int(match[1])
            if found != heading + 1:
                issues.append(issue(path, number, "heading-number", f"Expected {heading + 1}, found {found}."))
            heading = found
        for link in LINK.finditer(INLINE_CODE.sub("code", line)):
            target = link[1] or link[2]
            try:
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
                    continue
                local_path = in_repo(path.parent / unquote(parsed.path))
                exists = wiki_path(local_path) and (ROOT / local_path).exists()
            except ValueError:
                exists = False
            if not exists:
                issues.append(issue(path, number, "relative-link", f"Missing local target: {target}"))
    if fence:
        issues.append(issue(path, fence[1], "unclosed-fence", "Close the fenced block."))
    return issues


def read_page(path):
    return (ROOT / path).read_text(encoding="utf-8").splitlines()


def uncovered_changes(path, lines, claims):
    committed = subprocess.run(
        ["git", "show", f"HEAD:{path.as_posix()}"], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8",
    )
    # A new page has no committed baseline. Check each of its body lines.
    before = committed.stdout.splitlines() if committed.returncode == 0 else []
    changes = SequenceMatcher(a=before, b=lines, autojunk=False).get_opcodes()
    return {
        index + 1
        for kind, _, _, start, end in changes if kind in ("insert", "replace")
        for index in range(start, end) if lines[index] not in claims
    }


def validate_record(record):
    fields = ("page", "claim", "checked_on", "applies_to")
    if not isinstance(record, dict) or not all(
        isinstance(record.get(key), str) and record[key].strip() for key in fields
    ):
        raise ValueError("Each record needs page, claim, checked_on and applies_to.")
    checked_on = date.fromisoformat(record["checked_on"])
    if checked_on > date.today():
        raise ValueError("checked_on cannot be in the future.")
    return Path(record["page"]), checked_on


def validate_source(source):
    if not isinstance(source, dict) or ("url" in source) == ("path" in source):
        raise ValueError("Provide exactly one source URL or local path.")
    if "url" in source:
        value = source["url"]
        if not isinstance(value, str):
            raise ValueError("Source URL must be a string.")
        url = urlsplit(value)
        if url.scheme != "https" or not url.netloc or url.username or url.password:
            raise ValueError("Source URL must be public HTTPS without credentials.")
        if not isinstance(source.get("locator"), str) or not source["locator"].strip():
            raise ValueError("An external source needs a locator.")
        return
    source_path = Path(source["path"])
    if source_path.is_absolute() or not wiki_path(source_path) or in_repo(source_path) != source_path:
        raise ValueError("Local source must be a repository-relative path.")
    start, end = source["start"], source["end"]
    if type(start) is not int or type(end) is not int or not 1 <= start <= end:
        raise ValueError("Use inclusive, one-based source lines.")
    if not isinstance(source.get("quote"), str) or not source["quote"]:
        raise ValueError("A local source needs the exact quoted text.")
    lines = read_page(source_path)
    if end > len(lines) or "\n".join(lines[start - 1:end]) != source["quote"]:
        raise ValueError("Local source excerpt changed at the registered lines.")


def check_evidence(scope, pages, changed, max_age):
    if (ROOT / EVIDENCE).resolve() != ROOT / EVIDENCE:
        raise ValueError("Evidence must be a file in the repository.")
    records = json.loads((ROOT / EVIDENCE).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Evidence must be a JSON array.")
    verified_claims = {}
    issues = []
    due = []
    # A source-only edit must also trigger validation of the pages that cite it.
    touched = changed_paths(Path(".")) if changed else set()
    registry_changed = EVIDENCE in touched
    for index, record in enumerate(records, 1):
        try:
            path, checked_on = validate_record(record)
            if path.is_absolute() or not wiki_path(path) or path.suffix != ".md" or in_repo(path) != path:
                raise ValueError("Page must be a repository-relative Markdown path.")
            source = record.get("source")
            local_reference = source.get("path") if isinstance(source, dict) else None
            source_changed = isinstance(local_reference, str) and Path(local_reference) in touched
            if not within(path, scope) and not (source_changed and within(Path(local_reference), scope)):
                continue
            if changed and not (path in touched or registry_changed or source_changed):
                continue
            if record["claim"] not in read_page(path):
                raise ValueError(f"Registered claim line changed or was removed in {path}.")
            validate_source(source)
            if path in pages:
                verified_claims.setdefault(path, set()).add(record["claim"])
            if max_age is not None and (date.today() - checked_on).days > max_age:
                due.append({"page": path.as_posix(), "record": index, "checked_on": checked_on.isoformat()})
        except (ValueError, KeyError, TypeError, OSError) as error:
            issues.append(issue(EVIDENCE, None, "evidence", f"Record {index}. {error}"))
    return verified_claims, issues, due


def inspect(scope, changed=False, max_age=None, require_evidence=False):
    if require_evidence and (scope.suffix != ".md" or not (ROOT / scope).is_file()):
        raise ValueError("Use --require-evidence with --scope set to one Markdown file.")
    paths = markdown_paths(scope, changed)
    evidence, evidence_issues, due = check_evidence(scope, set(paths), changed, max_age)
    issues = []
    for path in paths:
        lines = read_page(path)
        uncovered = uncovered_changes(path, lines, evidence.get(path, ())) if require_evidence else ()
        issues.extend(check_markdown(path, lines, uncovered))
    return {
        "pages": len(paths), "pages_with_evidence": len(evidence),
        "pages_without_evidence": len(paths) - len(evidence),
        "issues": issues + evidence_issues, "due_for_recheck": due,
    }


def format_issue(item):
    where = f"{item['path']}:{item['line']}" if item["line"] else item["path"]
    return f"{where} [{item['code']}] {item['message']}"


def search_matches(scope, query):
    query = query.casefold()
    for path in markdown_paths(scope):
        for number, line in enumerate(read_page(path), 1):
            if query in line.casefold():
                yield path, number, line


def search(scope, query, limit):
    found = False
    for path, number, line in islice(search_matches(scope, query), limit):
        print(f"{path}:{number}: {line}")
        found = True
    return 0 if found else 1


def review(scope, preview, include_untracked):
    if scope == Path(".") or not (ROOT / scope).is_dir():
        raise ValueError("Choose a specific topic directory for CodeRabbit review.")
    paths = sorted(changed_paths(scope, include_untracked))
    if not paths:
        print(f"No reviewable changes under {scope}.")
        return 0
    if any(
        path.suffix != ".md" or not wiki_path(path) or (ROOT / path).resolve() != ROOT / path
        for path in paths
    ):
        raise ValueError("The topic has changes outside the wiki Markdown review scope.")
    command = [
        "coderabbit", "review", "--agent", "--uncommitted", "--dir", str(ROOT / scope),
        "--config", str(ROOT / "AGENTS.md"),
    ]
    if include_untracked:
        command.append("--include-untracked")
    if preview:
        print(shlex.join(command))
        print(*(path.as_posix() for path in paths), sep="\n")
        return 0
    failed = False
    with subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, text=True) as process:
        for line in process.stdout:
            print(line, end="", flush=True)
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            failed |= isinstance(event, dict) and event.get("type") == "error"
    return process.returncode or int(failed)


def stop_hook():
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise ValueError("Expected a Codex event object.")
    if payload.get("hook_event_name") != "Stop" or payload.get("stop_hook_active"):
        print("{}")
        return 0
    report = inspect(Path("."), changed=True)
    count = len(report["issues"])
    result = {}
    if count:
        result["systemMessage"] = (
            f"Lounge wiki check found {count} issue(s). Run python3 wiki/wiki.py check --changed."
        )
    print(json.dumps(result))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    find = commands.add_parser("search", help="Search local Markdown and print line locations.")
    find.add_argument("query")
    find.add_argument("--scope", default=".")
    find.add_argument("--limit", type=int, default=30)
    check = commands.add_parser("check", help="Check Markdown structure and registered evidence.")
    check.add_argument("--scope", default=".")
    check.add_argument("--changed", action="store_true")
    check.add_argument(
        "--require-evidence", action="store_true",
        help="Check evidence for changed body lines in one Markdown file.",
    )
    check.add_argument("--max-age", type=int, metavar="DAYS")
    check.add_argument("--json", action="store_true")
    code_review = commands.add_parser("review", help="Review one topic through CodeRabbit.")
    code_review.add_argument("scope")
    code_review.add_argument("--preview", action="store_true")
    code_review.add_argument("--include-untracked", action="store_true")
    commands.add_parser("hook", help="Read a Codex Stop event from stdin.")
    args = parser.parse_args()
    try:
        if args.command == "hook":
            return stop_hook()
        scope = get_scope(args.scope)
        if args.command == "search":
            if not args.query.strip() or args.limit < 1:
                raise ValueError("Use a non-empty query and a positive result limit.")
            return search(scope, args.query, args.limit)
        if args.command == "review":
            return review(scope, args.preview, args.include_untracked)
        if args.max_age is not None and args.max_age < 0:
            raise ValueError("--max-age must be zero or greater.")
        report = inspect(scope, args.changed, args.max_age, args.require_evidence)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            for item in report["issues"]:
                print(format_issue(item))
            for item in report["due_for_recheck"]:
                print(f"{item['page']} [recheck] {item['checked_on']} (record {item['record']})")
            print(
                f"{report['pages']} pages checked, {report['pages_with_evidence']} with evidence, "
                f"{len(report['issues'])} issues, {len(report['due_for_recheck'])} due for recheck."
            )
        return int(bool(report["issues"]))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        if args.command == "hook":
            print(json.dumps({"systemMessage": f"Lounge wiki check could not run: {error}"}))
            return 0
        print(f"Wiki error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
