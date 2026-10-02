#!/usr/bin/env python3
"""Reproduce the bounded tests and complete frozen finite campaign.

A clean run executes every campaign chunk.  With ``--resume``, a chunk is reused
only after its result JSON, CSV, stdout/stderr logs, suite identity, frozen case
count, and any retained generated-input file have all been checked.  Reused
results are recorded separately from commands actually executed in the current
invocation; no synthetic command receipt is created for a skipped chunk.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import resource
except ModuleNotFoundError:  # Native Windows does not provide this module.
    resource = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parent
WHOLE_TIMEOUT_SECONDS = 180.0
CHILD_TIMEOUT_SECONDS = 20.0
EXPECTED_TEST_METHODS = 22

EXPECTED_TOTALS = {
    "total_verdict_cases": 244_828,
    "total_summary_oracle_checks": 310_463,
    "total_whole_graph_oracle_checks": 244_824,
    "total_whole_graph_oracle_exclusions": 4,
    "total_raw_semantics_oracle_checks": 2_500,
    "exhaustive_binding_cases": 65_635,
    "refinement_checks": 1,
    "transfer_relation_candidates": 22_186,
    "accepted_transfer_relations": 1_358,
    "transfer_implication_checks": 2_116,
    "mismatches": 0,
}

EXPECTED_SUITE_CASES = {
    "core-2-0-625": 2_500,
    "core-3-0-2000": 24_000,
    "core-3-2000-4000": 24_000,
    "core-3-4000-6000": 24_000,
    "core-3-6000-8000": 24_000,
    "core-3-8000-10000": 24_000,
    "core-3-10000-12000": 24_000,
    "core-3-12000-14000": 24_000,
    "core-3-14000-16000": 24_000,
    "core-3-16000-18000": 24_000,
    "core-3-18000-19683": 20_196,
    "closed": 1_024,
    "modules": 512,
    "binding": 65_635,
    "refinement": 2,
    "transfer": 22_186,
    "raw": 2_500,
    "named": 26,
    "scaling": 30,
}

# Most CSV files retain one row per case.  Transfer retains two family aggregate
# rows, while refinement retains its two mode verdicts.
EXPECTED_CSV_DATA_ROWS = {
    **EXPECTED_SUITE_CASES,
    "transfer": 2,
    "refinement": 2,
}
EXPECTED_AUXILIARY_LINES = {
    "closed": ("closed-inputs.jsonl", 512, dict),
    "modules": ("modules-inputs.jsonl", 256, list),
}

COMMON_CASE_HEADER = [
    "case",
    "states",
    "tasks",
    "normalized_edges",
    "ports",
    "finite_changes",
    "live",
]
EXPECTED_CSV_HEADERS = {
    **{tag: ["edge_encoding", "port_bits", "initial", "live"]
       for tag in EXPECTED_SUITE_CASES if tag.startswith("core-")},
    "closed": COMMON_CASE_HEADER,
    "modules": COMMON_CASE_HEADER,
    "binding": [
        "family",
        "encoding_a",
        "encoding_b",
        "summary_arcs",
        "divergence_ports",
    ],
    "refinement": COMMON_CASE_HEADER,
    "transfer": [
        "family",
        "relation_candidates",
        "accepted_relations",
        "implication_checks",
    ],
    "raw": ["family", "edge_encoding", "finite_changes", "live"],
    "named": COMMON_CASE_HEADER,
    "scaling": [
        "states",
        "tasks",
        "returning_ring",
        "normalized_edges",
        "summary_arcs",
        "live",
        "wall_seconds",
        "whole_graph_oracle_used",
    ],
}

Job = tuple[str, int, int, int]


def _jobs() -> list[Job]:
    jobs: list[Job] = [("core", 2, 0, 625)]
    jobs.extend(
        ("core", 3, begin, min(begin + 2_000, 19_683))
        for begin in range(0, 19_683, 2_000)
    )
    jobs.extend(
        (kind, 0, 0, 0)
        for kind in (
            "closed",
            "modules",
            "binding",
            "refinement",
            "transfer",
            "raw",
            "named",
            "scaling",
        )
    )
    return jobs


def _job_tag(job: Job) -> str:
    kind, states, begin, end = job
    return f"core-{states}-{begin}-{end}" if kind == "core" else kind


def _source_parameters(job: Job) -> dict[str, Any]:
    kind, states, begin, end = job
    if kind == "core":
        return {"campaign": kind, "states": states, "start": begin, "stop": end}
    return {"campaign": kind}


def _job_argv(job: Job, output: Path) -> list[str]:
    kind, states, begin, end = job
    argv = [sys.executable, "src/campaign.py", kind, "--out", str(output)]
    if kind == "core":
        argv.extend(["--n", str(states), "--start", str(begin), "--stop", str(end)])
    return argv


def _portable_command(argv: list[str], output: Path) -> list[str]:
    """Remove machine-private paths from the retained command record."""
    result: list[str] = []
    for index, value in enumerate(argv):
        if index == 0:
            result.append("python3")
        elif value == str(output):
            result.append("<output>")
        else:
            result.append(value)
    return result


def _required_suite_paths(output: Path, job: Job) -> list[Path]:
    tag = _job_tag(job)
    paths = [
        output / f"{tag}.json",
        output / f"{tag}.csv",
        output / f"{tag}.stdout.txt",
        output / f"{tag}.stderr.txt",
    ]
    if tag in EXPECTED_AUXILIARY_LINES:
        paths.append(output / EXPECTED_AUXILIARY_LINES[tag][0])
    return paths


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is unreadable or invalid JSON") from exc
    if type(value) is not dict:
        raise ValueError(f"{label} is not a JSON object")
    return value


def _validate_suite_bundle(output: Path, job: Job) -> dict[str, Any]:
    """Validate one completed campaign bundle before execution can be skipped."""
    tag = _job_tag(job)
    paths = _required_suite_paths(output, job)
    missing = [path.name for path in paths if not path.is_file()]
    if missing:
        raise ValueError(f"missing retained artifacts: {', '.join(missing)}")

    result = _load_json_object(output / f"{tag}.json", f"{tag}.json")
    required = {
        "suite",
        "cases",
        "verdict_cases",
        "summary_oracle_checks",
        "whole_graph_oracle_checks",
        "whole_graph_oracle_exclusions",
        "raw_semantics_oracle_checks",
        "nonlive",
        "mismatches",
        "wall_seconds",
        "cpu_seconds",
        "peak_rss_kib",
        "workers",
    }
    if not required <= result.keys():
        raise ValueError(f"{tag}.json is missing required result fields")
    if result["suite"] != tag:
        raise ValueError(
            f"suite/source-parameter mismatch: {result['suite']!r} != {tag!r}"
        )
    if result["cases"] != EXPECTED_SUITE_CASES[tag]:
        raise ValueError(
            f"case-count mismatch for {tag}: {result['cases']!r} != "
            f"{EXPECTED_SUITE_CASES[tag]!r}"
        )
    integer_fields = required - {"suite", "wall_seconds", "cpu_seconds"}
    if any(type(result[field]) is not int for field in integer_fields):
        raise ValueError(f"{tag}.json has a non-integer count/resource field")
    if result["workers"] != 1 or result["mismatches"] != 0:
        raise ValueError(f"{tag}.json does not record one worker and zero mismatches")

    stdout_path = output / f"{tag}.stdout.txt"
    try:
        lines = [line for line in stdout_path.read_text().splitlines() if line.strip()]
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"{tag}.stdout.txt is unreadable") from exc
    if len(lines) != 1:
        raise ValueError(f"{tag}.stdout.txt must contain exactly one JSON receipt")
    try:
        stdout_result = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise ValueError(f"{tag}.stdout.txt does not contain valid JSON") from exc
    if stdout_result != result:
        raise ValueError(f"{tag}.stdout.txt does not match {tag}.json")

    stderr_path = output / f"{tag}.stderr.txt"
    try:
        stderr_text = stderr_path.read_text()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"{tag}.stderr.txt is unreadable") from exc
    if stderr_text:
        raise ValueError(f"{tag}.stderr.txt is not empty")

    csv_path = output / f"{tag}.csv"
    try:
        with csv_path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            header = reader.fieldnames
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"{tag}.csv is unreadable or malformed") from exc
    if header != EXPECTED_CSV_HEADERS[tag]:
        raise ValueError(
            f"CSV header mismatch for {tag}: {header!r} != "
            f"{EXPECTED_CSV_HEADERS[tag]!r}"
        )
    if len(rows) != EXPECTED_CSV_DATA_ROWS[tag]:
        raise ValueError(
            f"CSV row-count mismatch for {tag}: {len(rows)} != "
            f"{EXPECTED_CSV_DATA_ROWS[tag]}"
        )

    # Core suite names encode the exact enumeration parameters.  Validate that
    # the retained CSV covers every permitted (encoding, port set, port initial)
    # tuple exactly once, so a same-sized CSV from another chunk cannot be reused.
    if tag.startswith("core-"):
        _, states, begin, end = job
        multiplicity = states * (1 << (states - 1))
        counts = {encoding: 0 for encoding in range(begin, end)}
        seen: set[tuple[int, int, int]] = set()
        try:
            for row in rows:
                encoding = int(row["edge_encoding"])
                port_bits = int(row["port_bits"])
                initial = int(row["initial"])
                live = int(row["live"])
                if encoding not in counts:
                    raise ValueError("edge encoding lies outside the named chunk")
                if not (0 < port_bits < (1 << states)):
                    raise ValueError("port bitset is outside the named state range")
                if not (0 <= initial < states and port_bits & (1 << initial)):
                    raise ValueError("initial state is not a member of the port set")
                if live not in (0, 1):
                    raise ValueError("live field is not Boolean")
                key = (encoding, port_bits, initial)
                if key in seen:
                    raise ValueError("duplicate core-enumeration row")
                seen.add(key)
                counts[encoding] += 1
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{tag}.csv does not match its source parameters") from exc
        if any(count != multiplicity for count in counts.values()):
            raise ValueError(f"{tag}.csv does not completely cover its source range")

    if tag == "transfer":
        try:
            by_family = {row["family"]: row for row in rows}
            if set(by_family) != {"ordinary", "marked"}:
                raise ValueError("unexpected transfer family inventory")
            relation_candidates = sum(
                int(row["relation_candidates"]) for row in rows
            )
            accepted = sum(int(row["accepted_relations"]) for row in rows)
            implications = sum(int(row["implication_checks"]) for row in rows)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("transfer.csv is inconsistent with its schema") from exc
        if (
            relation_candidates != result.get("transfer_relation_candidates")
            or accepted != result.get("accepted_transfer_relations")
            or implications != result.get("transfer_implication_checks")
        ):
            raise ValueError("transfer.csv aggregate fields do not match transfer.json")

    if tag in EXPECTED_AUXILIARY_LINES:
        filename, expected_lines, expected_type = EXPECTED_AUXILIARY_LINES[tag]
        observed_lines = 0
        try:
            with (output / filename).open() as handle:
                for observed_lines, line in enumerate(handle, start=1):
                    value = json.loads(line)
                    if type(value) is not expected_type:
                        raise ValueError("unexpected generated-input record type")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"{filename} is unreadable or malformed") from exc
        if observed_lines != expected_lines:
            raise ValueError(
                f"generated-input count mismatch for {filename}: "
                f"{observed_lines} != {expected_lines}"
            )
    return result


def _classify_resume(
    output: Path, jobs: list[Job]
) -> tuple[list[dict[str, Any]], list[Job], list[dict[str, str]]]:
    """Partition jobs into validated reuse, execution, and invalid prior records."""
    reused: list[dict[str, Any]] = []
    pending: list[Job] = []
    invalid: list[dict[str, str]] = []
    for job in jobs:
        tag = _job_tag(job)
        paths = _required_suite_paths(output, job)
        if not any(path.exists() for path in paths):
            pending.append(job)
            continue
        try:
            result = _validate_suite_bundle(output, job)
        except ValueError as exc:
            pending.append(job)
            invalid.append({"suite": tag, "reason": str(exc), "action": "recomputed"})
            continue
        reused.append(
            {
                "suite": tag,
                "source_parameters": _source_parameters(job),
                "validated_artifacts": [path.name for path in paths],
                "result": result,
            }
        )
    return reused, pending, invalid


def _aggregate_suites(suites: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the frozen scientific totals independently of execution provenance."""
    return {
        "suites": suites,
        "total_verdict_cases": sum(suite["verdict_cases"] for suite in suites),
        "total_summary_oracle_checks": sum(
            suite["summary_oracle_checks"] for suite in suites
        ),
        "total_whole_graph_oracle_checks": sum(
            suite["whole_graph_oracle_checks"] for suite in suites
        ),
        "total_whole_graph_oracle_exclusions": sum(
            suite["whole_graph_oracle_exclusions"] for suite in suites
        ),
        "total_raw_semantics_oracle_checks": sum(
            suite.get("raw_semantics_oracle_checks", 0) for suite in suites
        ),
        "exhaustive_binding_cases": next(
            suite["cases"] for suite in suites if suite["suite"] == "binding"
        ),
        "refinement_checks": next(
            suite.get("refinement_checks", 0)
            for suite in suites
            if suite["suite"] == "refinement"
        ),
        "transfer_relation_candidates": next(
            suite.get("transfer_relation_candidates", 0)
            for suite in suites
            if suite["suite"] == "transfer"
        ),
        "accepted_transfer_relations": next(
            suite.get("accepted_transfer_relations", 0)
            for suite in suites
            if suite["suite"] == "transfer"
        ),
        "transfer_implication_checks": next(
            suite.get("transfer_implication_checks", 0)
            for suite in suites
            if suite["suite"] == "transfer"
        ),
        "mismatches": sum(suite["mismatches"] for suite in suites),
    }


def _require_supported_environment() -> None:
    if (
        os.name != "posix"
        or resource is None
        or not hasattr(os, "killpg")
        or not hasattr(signal, "SIGKILL")
    ):
        raise RuntimeError(
            "reproduce.py requires a POSIX process environment with the Python "
            "resource module, process groups, and SIGKILL. Native Windows is not "
            "supported; use the documented Linux path."
        )
    if not (sys.platform.startswith("linux") or sys.platform == "darwin"):
        raise RuntimeError(
            "reproduce.py does not know the ru_maxrss unit on this POSIX platform; "
            "the verified path is Linux (the macOS conversion is explicit but untested)."
        )


def _native_rss_unit() -> str:
    return "bytes" if sys.platform == "darwin" else "KiB"


def _rss_kib(who: int) -> int:
    assert resource is not None
    value = resource.getrusage(who).ru_maxrss
    return int((value + 1023) // 1024) if sys.platform == "darwin" else int(value)


def _environment_record() -> dict[str, Any]:
    return {
        "operating_system": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_executable_name": Path(sys.executable).name,
        "resource_module": "available",
        "process_group_api": "start_new_session plus os.killpg",
        "ru_maxrss_native_unit": _native_rss_unit(),
        "reported_peak_rss_unit": "KiB",
    }


def _validate_result(result: dict[str, Any], output: Path, jobs: list[Job]) -> None:
    suites = result["suites"]
    observed_suite_cases = {entry["suite"]: entry["cases"] for entry in suites}
    if observed_suite_cases != EXPECTED_SUITE_CASES:
        raise RuntimeError(
            "suite inventory/count drift: "
            f"observed={observed_suite_cases!r}, expected={EXPECTED_SUITE_CASES!r}"
        )

    for key, expected in EXPECTED_TOTALS.items():
        observed = result.get(key)
        if observed != expected:
            raise RuntimeError(
                f"deterministic total drift for {key}: {observed!r} != {expected!r}"
            )

    test_log = (output / "tests.stderr.txt").read_text()
    methods = len(re.findall(r"^test_.* \.\.\. ok$", test_log, re.MULTILINE))
    if methods != EXPECTED_TEST_METHODS or not re.search(r"^OK$", test_log, re.MULTILINE):
        raise RuntimeError(
            f"unit-test receipt drift: found {methods} passing methods and "
            f"OK={bool(re.search(r'^OK$', test_log, re.MULTILINE))}"
        )

    commands = result["commands_executed_this_run"]
    if not commands or commands[0].get("tag") != "tests":
        raise RuntimeError("the current invocation must actually execute the unit tests")
    if any(command.get("exit_code") != 0 for command in commands):
        raise RuntimeError("a current-run command has a nonzero exit code")
    command_tags = [command.get("tag") for command in commands]
    if len(command_tags) != len(set(command_tags)):
        raise RuntimeError("duplicate current-run command receipt")
    executed_suites = set(command_tags) - {"tests"}

    reused_records = result["results_reused_after_validation"]
    reused_suites = {record["suite"] for record in reused_records}
    expected_suites = {_job_tag(job) for job in jobs}
    if executed_suites & reused_suites:
        raise RuntimeError("a suite is recorded as both executed and reused")
    if executed_suites | reused_suites != expected_suites:
        raise RuntimeError("executed and reused suites do not form the complete inventory")
    if len(commands) != 1 + len(executed_suites):
        raise RuntimeError("current-run command receipts do not match actual executions")

    expected_parameters = {_job_tag(job): _source_parameters(job) for job in jobs}
    for record in reused_records:
        if record.get("source_parameters") != expected_parameters.get(record.get("suite")):
            raise RuntimeError("a reused result has mismatched source parameters")
    if result["execution_mode"] == "clean" and reused_records:
        raise RuntimeError("a clean run cannot reuse prior suite results")
    for record in result["invalid_resume_records_recomputed"]:
        if record.get("suite") not in executed_suites:
            raise RuntimeError("an invalid resume record was not actually recomputed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "reproduced", help="new result directory"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "reuse only fully validated suite bundles in an existing output; "
            "missing or damaged bundles are recomputed"
        ),
    )
    args = parser.parse_args()
    _require_supported_environment()
    output = args.output.resolve()

    if output.exists() and not args.resume:
        raise ValueError("output already exists; use a new directory or explicit --resume")
    output.mkdir(parents=True, exist_ok=True)

    jobs = _jobs()
    if args.resume:
        reused_with_results, pending_jobs, invalid_records = _classify_resume(output, jobs)
    else:
        reused_with_results, pending_jobs, invalid_records = [], jobs, []

    start = time.monotonic()
    commands: list[dict[str, Any]] = []

    def run(argv: list[str], tag: str) -> None:
        remaining = WHOLE_TIMEOUT_SECONDS - (time.monotonic() - start)
        if remaining <= 0:
            raise TimeoutError("whole reproduction time limit reached")

        command_start = time.monotonic()
        stdout_path = output / f"{tag}.stdout.txt"
        stderr_path = output / f"{tag}.stderr.txt"
        print(f"[reproduce] {tag}", file=sys.stderr, flush=True)

        with stdout_path.open("w") as stdout_handle, stderr_path.open("w") as stderr_handle:
            process = subprocess.Popen(
                argv,
                cwd=ROOT,
                text=True,
                stdout=stdout_handle,
                stderr=stderr_handle,
                start_new_session=True,
            )
            try:
                process.wait(timeout=min(CHILD_TIMEOUT_SECONDS, remaining))
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                raise TimeoutError(f"bounded command timed out: {tag}") from None

        commands.append(
            {
                "tag": tag,
                "command": _portable_command(argv, output),
                "exit_code": process.returncode,
                "wall_seconds": time.monotonic() - command_start,
            }
        )
        if process.returncode != 0:
            raise RuntimeError(f"failed bounded command: {tag}")

    # Tests are always re-executed against the current source, even on resume.
    run([sys.executable, "tests/test_core.py"], "tests")

    for job in pending_jobs:
        tag = _job_tag(job)
        run(_job_argv(job, output), tag)
        _validate_suite_bundle(output, job)

    # Revalidate every bundle after all writes and aggregate in the frozen order.
    suites = [_validate_suite_bundle(output, job) for job in jobs]
    result = _aggregate_suites(suites)
    reused_records = [
        {key: value for key, value in entry.items() if key != "result"}
        for entry in reused_with_results
    ]
    assert resource is not None
    result.update(
        {
            "execution_mode": "resume" if args.resume else "clean",
            "wall_seconds": time.monotonic() - start,
            "measured_child_cpu_seconds": (
                resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime
                + resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime
            ),
            "parent_cpu_seconds": time.process_time(),
            "peak_child_rss_kib": _rss_kib(resource.RUSAGE_CHILDREN),
            "peak_parent_rss_kib": _rss_kib(resource.RUSAGE_SELF),
            "max_concurrent_scientific_workers": 1,
            "environment": _environment_record(),
            "commands_executed_this_run": commands,
            "results_reused_after_validation": reused_records,
            "invalid_resume_records_recomputed": invalid_records,
            "resume_note": (
                "A reused suite has no current-run command receipt. It is listed only "
                "under results_reused_after_validation after its JSON, CSV, logs, suite "
                "identity, frozen case count, and retained generated inputs are checked."
            ),
        }
    )

    _validate_result(result, output, jobs)
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    concise = {
        key: value
        for key, value in result.items()
        if key
        not in {
            "suites",
            "commands_executed_this_run",
            "results_reused_after_validation",
        }
    }
    print(json.dumps(concise, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (
        OSError,
        ValueError,
        RuntimeError,
        TimeoutError,
        subprocess.TimeoutExpired,
    ) as exc:
        print(f"REPRODUCTION FAILED: {exc}", file=sys.stderr)
        sys.exit(2)
