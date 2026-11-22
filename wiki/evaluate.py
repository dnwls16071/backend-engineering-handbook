#!/usr/bin/env python3
"""Evaluate Lounge search and answer citations, then compare two runs."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import wiki


DATASET = Path(__file__).with_name("evaluation-cases.json")
SCHEMA_VERSION = 1


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def markdown_path(value):
    if not nonempty(value):
        return False
    path = Path(value)
    return (
        not path.is_absolute() and path.as_posix() == value
        and path.suffix == ".md" and wiki.wiki_path(path) and ".." not in path.parts
    )


def load_dataset(path):
    raw = path.read_bytes()
    cases = json.loads(raw.decode("utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("The dataset must be a non-empty array.")
    ids = set()
    for index, case in enumerate(cases, 1):
        if not isinstance(case, dict) or not all(
            nonempty(case.get(field)) for field in ("id", "question", "query", "scope")
        ):
            raise ValueError(f"Case {index} needs an id, question, query, and scope.")
        case_id = case["id"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", case_id) or case_id in ids:
            raise ValueError(f"Case ID must be unique and use lowercase words separated by hyphens: {case_id}")
        ids.add(case_id)
        scope = Path(case["scope"])
        if scope.is_absolute() or not wiki.wiki_path(scope) or ".." in scope.parts:
            raise ValueError(f"{case_id} needs a repository-relative scope.")
        pages = case.get("expected_pages")
        facts = case.get("facts")
        if not isinstance(pages, list) or not all(markdown_path(page) for page in pages):
            raise ValueError(f"{case_id} needs an expected_pages array of relative Markdown paths.")
        if not isinstance(facts, list) or bool(pages) != bool(facts) or not all(
            isinstance(fact, list) and fact and all(nonempty(term) for term in fact) for fact in facts
        ):
            raise ValueError(f"{case_id} needs facts as arrays of terms, or no facts for an abstention case.")
    return cases, hashlib.sha256(raw).hexdigest()


def questions(cases):
    return [
        {key: case[key] for key in ("id", "question", "query", "scope")}
        for case in cases
    ]


def retrieve(case, top_k):
    scope = Path(case["scope"])
    if not (wiki.ROOT / scope).exists():
        return []
    scope = wiki.get_scope(case["scope"])
    hits = {}
    for path, line, quote in wiki.search_matches(scope, case["query"]):
        page = path.as_posix()
        if page not in hits:
            hits[page] = {"path": page, "line": line, "quote": quote}
            if len(hits) == top_k:
                break
    return list(hits.values())


def extract_answer(hits):
    if not hits:
        return {"status": "insufficient_evidence", "answer": "검색 결과에서 근거를 찾지 못했습니다.", "citations": []}
    return {"status": "answered", "answer": hits[0]["quote"], "citations": [hits[0]]}


def citation_excerpt(citation, allowed_pages):
    if not isinstance(citation, dict):
        raise ValueError("Citation must be an object.")
    page, line, quote = (citation.get(key) for key in ("path", "line", "quote"))
    if not markdown_path(page) or page not in allowed_pages:
        raise ValueError(f"Unexpected citation path: {page!r}")
    if type(line) is not int or line < 1 or not nonempty(quote):
        raise ValueError(f"{page} requires a positive line number and a verbatim quote.")
    path = Path(page)
    if wiki.in_repo(path) != path:
        raise ValueError(f"{page} does not resolve to its repository path.")
    try:
        lines = wiki.read_page(path)
    except (OSError, UnicodeError) as error:
        raise ValueError(f"Unable to read citation at {page}:{line}.") from error
    if line > len(lines) or lines[line - 1] != quote:
        raise ValueError(f"The quote does not match {page}:{line}.")
    return quote


def mentions_fact(text, fact):
    text = text.casefold()
    return all(term.casefold() in text for term in fact)


def location(hit):
    return {"path": hit["path"], "line": hit["line"]}


def check_answer(case, answer):
    if not isinstance(answer, dict):
        return {"answer": ["Missing answer object."]}, []
    status, text, citations = (answer.get(key) for key in ("status", "answer", "citations"))
    if not nonempty(text) or not isinstance(citations, list):
        return {"answer": ["An answer needs non-empty text and an array of citations."]}, []
    allowed_pages = case["expected_pages"]
    if not allowed_pages:
        if status == "insufficient_evidence" and not citations:
            return {}, []
        return {"answer": ["Expected insufficient_evidence with no citations."]}, []
    if status != "answered":
        return {"answer": ["Expected an answer with supporting citations."]}, []

    failures, excerpts, locations = {}, [], []
    if not citations:
        failures["citation"] = ["Expected at least one citation."]
    for citation in citations:
        try:
            excerpts.append(citation_excerpt(citation, allowed_pages))
            locations.append(location(citation))
        except ValueError as error:
            failures.setdefault("citation", []).append(str(error))
    for fact in case["facts"]:
        terms = " + ".join(fact)
        if not mentions_fact(text, fact):
            failures.setdefault("answer", []).append(f"Expected answer terms: {terms}")
        if not any(mentions_fact(excerpt, fact) for excerpt in excerpts):
            failures.setdefault("support", []).append(f"Expected a cited line with: {terms}")
    return failures, locations


def run_cases(cases, top_k, answers=None):
    results = []
    for case in cases:
        hits = retrieve(case, top_k)
        expected = case["expected_pages"]
        rank = next((index for index, hit in enumerate(hits, 1) if hit["path"] in expected), None)
        answer = extract_answer(hits) if answers is None else answers.get(case["id"])
        failures, citations = check_answer(case, answer)
        if expected and rank is None:
            failures["search"] = [f"No expected document in the top {top_k}: {', '.join(expected)}"]
        elif not expected and hits:
            failures["search"] = ["Expected no matches for the missing-evidence query."]
        results.append({
            "id": case["id"], "question": case["question"], "rank": rank,
            "retrieved": [location(hit) for hit in hits], "citations": citations,
            "failures": failures,
        })
    return results


def compare(before, after):
    fields = ("schema_version", "dataset_sha256", "top_k", "mode")
    if before["schema_version"] != SCHEMA_VERSION or any(before[field] != after[field] for field in fields):
        raise ValueError("Compare reports with the same schema, dataset, top-k and answer mode.")
    previous = {case["id"]: case for case in before["cases"]}
    current = {case["id"]: case for case in after["cases"]}
    if (previous.keys() != current.keys() or len(previous) != len(before["cases"])
            or len(current) != len(after["cases"])):
        raise ValueError("Reports must have the same unique case IDs.")
    changes = []
    for case_id, case in current.items():
        old = previous[case_id]["failures"]
        new = case["failures"]
        if not old and not new:
            continue
        changes.append({
            "id": case_id, "question": case["question"],
            "new": {key: new[key] for key in sorted(new.keys() - old.keys())},
            "resolved": {key: old[key] for key in sorted(old.keys() - new.keys())},
            "persistent": {key: new[key] for key in sorted(old.keys() & new.keys())},
        })
    return changes


def print_failures(failures):
    for category, messages in failures.items():
        for message in messages:
            print(f"  [{category}] {message}")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    sheet = commands.add_parser("questions", help="Export questions without the grading criteria.")
    run = commands.add_parser("run", help="Run the evaluation and save a JSON report.")
    for command in (sheet, run):
        command.add_argument("--cases", type=Path, default=DATASET)
    run.add_argument("--answers", type=Path, help="Use supplied LLM answers instead of local excerpts.")
    run.add_argument("--top-k", type=int, default=5)
    run.add_argument("--out", type=Path, required=True)
    diff = commands.add_parser("compare", help="Show new, resolved and persistent failures.")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "compare":
            changes = compare(read_json(args.before), read_json(args.after))
            for status in ("new", "resolved", "persistent"):
                cases = [case for case in changes if case[status]]
                print(f"{status.capitalize()} failures: {len(cases)} case(s)")
                for case in cases:
                    print(f"- {case['id']} — {case['question']}")
                    print_failures(case[status])
            return int(any(case["new"] for case in changes))

        cases, digest = load_dataset(args.cases)
        if args.command == "questions":
            print(json.dumps(questions(cases), ensure_ascii=False, indent=2))
            return 0
        if args.top_k < 1:
            raise ValueError("--top-k must be positive.")
        inputs = [args.cases, wiki.ROOT / wiki.EVIDENCE]
        if args.answers is not None:
            inputs.append(args.answers)
        if any(args.out.resolve() == path.resolve() for path in inputs):
            raise ValueError("--out must differ from the input files.")
        answers = None
        if args.answers is not None:
            answers = read_json(args.answers)
            if not isinstance(answers, dict) or answers.keys() - {case["id"] for case in cases}:
                raise ValueError("Answer JSON must be an object keyed by known case IDs.")

        results = run_cases(cases, args.top_k, answers)
        failed = [case for case in results if case["failures"]]
        report = {
            "schema_version": SCHEMA_VERSION, "dataset_sha256": digest, "top_k": args.top_k,
            "mode": "extractive" if answers is None else "external",
            "passed": len(results) - len(failed), "failed": len(failed), "cases": results,
        }
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{report['passed']}/{len(results)} cases passed ({report['mode']}). Report: {args.out}")
        for case in failed:
            print(f"- {case['id']} — {case['question']}")
            print_failures(case["failures"])
            if case["retrieved"]:
                print("  Retrieved: " + ", ".join(f"{hit['path']}:{hit['line']}" for hit in case["retrieved"]))
        return int(bool(failed))
    except (ValueError, TypeError, KeyError, AttributeError, OSError, subprocess.CalledProcessError) as error:
        print(f"Evaluation error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
