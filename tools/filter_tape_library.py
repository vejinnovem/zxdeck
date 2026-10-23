#!/usr/bin/env python3
"""Copy structurally valid tape images into a clean device library."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import shutil

from zxdeck.tape import probe_tape_bytes


CANDIDATE_SUFFIXES = {".tap", ".tzx", ".pzx"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--include-checksum-warnings",
        action="store_true",
        help="include structurally valid TAP files whose block XOR is non-zero",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    destination = args.destination.resolve()
    if not source.is_dir():
        raise SystemExit(f"source is not a directory: {source}")
    if destination == source or source in destination.parents:
        raise SystemExit("destination must not be inside the source tree")
    destination.mkdir(parents=True, exist_ok=True)

    counts: Counter[str] = Counter()
    report: list[str] = ["result\tdeclared\tdetected\tchecksums\tpath"]
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        suffix = path.suffix.casefold()
        if suffix not in CANDIDATE_SUFFIXES:
            counts["unsupported"] += 1
            report.append(f"unsupported\t{suffix}\t\t\t{relative}")
            continue

        probe = probe_tape_bytes(path.read_bytes(), suffix)
        accepted = probe.strict or (
            args.include_checksum_warnings and probe.valid
        )
        if not accepted:
            result = "checksum-warning" if probe.valid else "invalid"
            counts[result] += 1
            report.append(
                f"{result}\t{suffix}\t{probe.detected_format or ''}\t"
                f"{probe.checksum_failures}\t{relative}"
            )
            continue

        target_relative = relative
        if probe.canonical_suffix and suffix != probe.canonical_suffix:
            target_relative = relative.with_suffix(probe.canonical_suffix)
            counts["renamed"] += 1
        target = destination / target_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        counts[f"accepted-{probe.detected_format}"] += 1
        report.append(
            f"accepted\t{suffix}\t{probe.detected_format}\t"
            f"{probe.checksum_failures}\t{target_relative}"
        )

    report_path = destination / "_zxdeck-filter-report.tsv"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    for key in sorted(counts):
        print(f"{key}: {counts[key]}")
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
