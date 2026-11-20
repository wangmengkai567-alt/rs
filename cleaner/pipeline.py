import argparse
import base64
import csv
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from time import perf_counter

from filelock import FileLock, Timeout

from cleaner.schema import (
    CLEAN_HEADER,
    REASONS,
    RULE_VERSION,
    parse_coords,
    parse_id,
    parse_utc,
    sha256_file,
)


class OutOfOrder(ValueError):
    pass


def process_rows(source, clean, rejects):
    writer = csv.writer(clean, delimiter="\t", lineterminator="\n")
    writer.writerow(CLEAN_HEADER)
    digest = hashlib.sha256()
    reasons = Counter(dict.fromkeys(REASONS, 0))
    sites = set()
    user_id = None
    previous_time = ""
    first_time = last_time = None
    seen = set()
    coords_by_key = {}
    conflicting_keys = set()
    input_count = clean_count = user_count = conflict_count = 0

    for input_count, raw_line in enumerate(source, 1):
        digest.update(raw_line)
        raw = raw_line.removesuffix(b"\n").removesuffix(b"\r")
        text = None
        reason = None
        try:
            text = raw.decode("utf-8")
            fields = text.split("\t")
            if len(fields) != 5 or not all(fields):
                raise ValueError
        except ValueError:
            reason = "BAD_STRUCT"

        if reason is None:
            user, ts, latitude, longitude, location = fields
            try:
                uid = parse_id(user)
                pid = parse_id(location)
            except ValueError:
                reason = "BAD_ID"

        if reason is None:
            if uid != user_id:
                if user_id is not None and uid < user_id:
                    raise OutOfOrder(f"line {input_count}: user ID decreased")
                if seen:
                    user_count += 1
                conflict_count += len(conflicting_keys)
                seen.clear()
                coords_by_key.clear()
                conflicting_keys.clear()
                user_id, previous_time = uid, ""
            try:
                parse_utc(ts)
            except ValueError:
                reason = "BAD_TIME"
            else:
                if previous_time and ts > previous_time:
                    raise OutOfOrder(f"line {input_count}: timestamp increased within user {uid}")
                previous_time = ts

        if reason is None:
            try:
                lat, lon = parse_coords(latitude, longitude)
            except ValueError:
                reason = "BAD_COORD"
            else:
                if (lat, lon) == (0, 0):
                    reason = "ZERO_COORD"

        if reason is None:
            record_key = (ts, pid, lat, lon)
            if record_key in seen:
                reason = "DUPLICATE"
            else:
                seen.add(record_key)
                key = (ts, pid)
                if coords_by_key.setdefault(key, (lat, lon)) != (lat, lon):
                    conflicting_keys.add(key)
                writer.writerow((input_count, uid, ts, latitude, longitude, pid))
                clean_count += 1
                sites.add(pid)
                first_time = ts if first_time is None else min(first_time, ts)
                last_time = ts if last_time is None else max(last_time, ts)

        if reason is not None:
            reasons[reason] += 1
            record = {"source_line": input_count, "reason_code": reason}
            if text is None:
                record["raw_base64"] = base64.b64encode(raw).decode("ascii")
            else:
                record["raw"] = text
            rejects.write(json.dumps(record, ensure_ascii=False) + "\n")

        if input_count % 1_000_000 == 0:
            print(f"Scanned {input_count:,} rows", flush=True)

    return {
        "input_sha256": digest.hexdigest(),
        "input_count": input_count,
        "clean_count": clean_count,
        "reject_count": sum(reasons.values()),
        "reason_counts": dict(reasons),
        "conflicting_keys": conflict_count + len(conflicting_keys),
        "user_count": user_count + bool(seen),
        "location_count": len(sites),
        "first_ts_utc": first_time,
        "last_ts_utc": last_time,
    }


def clean_file(source: Path, output: Path) -> dict:
    start = perf_counter()
    output.mkdir(parents=True, exist_ok=True)
    output_paths = [output / name for name in ("clean.tsv", "reject.ndjson", "quality_report.json")]
    if source.resolve() in [path.resolve() for path in output_paths]:
        raise ValueError("Input must be different from the output files")
    with FileLock(output / ".pipeline.lock", timeout=0):
        with tempfile.TemporaryDirectory(dir=output, prefix=".cleaning-") as temporary:
            clean_path, reject_path, report_path = [Path(temporary) / path.name for path in output_paths]
            with (
                source.open("rb") as rows,
                clean_path.open("w", encoding="utf-8", newline="\n") as clean,
                reject_path.open("w", encoding="utf-8", newline="\n") as rejects,
            ):
                report = process_rows(rows, clean, rejects)
            report.update(
                input_file=source.name,
                rule_version=RULE_VERSION,
                clean_sha256=sha256_file(clean_path),
                elapsed_seconds=round(perf_counter() - start, 3),
            )
            report_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8", newline="\n",
            )
            output_paths[2].unlink(missing_ok=True)
            for temporary_path, output_path in zip((clean_path, reject_path, report_path), output_paths):
                temporary_path.replace(output_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean the Gowalla check-in file")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = clean_file(args.input, args.output)
    except (OSError, ValueError, Timeout) as error:
        print(f"Cleaning failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
