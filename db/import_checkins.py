import argparse
import csv
import json
import re
import sys
import tempfile
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter, sleep

from filelock import FileLock, Timeout
from pymongo import MongoClient, UpdateOne
from pymongo.errors import PyMongoError

from cleaner.schema import CLEAN_HEADER, REASONS, RULE_VERSION, parse_coords, parse_id, parse_utc
from cleaner.schema import sha256_file

DEFAULT_URI = "mongodb://127.0.0.1:27017"
DATABASE = "gowalla"
NAMESPACE = f"{DATABASE}.checkins"
SHARDS = {"shard1", "shard2"}
MANIFEST_ID = "current"
BATCH_SIZE = 5000
WRITE_WORKERS = 4
DIGEST_FORMAT = re.compile(r"[0-9a-f]{64}")


def load_report(path: Path, clean_path: Path) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("rule_version") != RULE_VERSION:
        raise ValueError("Unsupported quality report version")
    counters = ("input_count", "clean_count", "reject_count", "user_count", "location_count")
    if any(type(report.get(key)) is not int or report[key] < 0 for key in counters):
        raise ValueError("Invalid counts in quality report")
    reasons = report.get("reason_counts")
    if not isinstance(reasons, dict) or set(reasons) != set(REASONS) or any(
        type(count) is not int or count < 0 for count in reasons.values()
    ):
        raise ValueError("Invalid reject reason counts in quality report")
    if (
        report["clean_count"] == 0
        or report["input_count"] != report["clean_count"] + report["reject_count"]
        or report["reject_count"] != sum(reasons.values())
    ):
        raise ValueError("Quality report does not reconcile")
    for key in ("input_sha256", "clean_sha256"):
        if DIGEST_FORMAT.fullmatch(str(report.get(key))) is None:
            raise ValueError(f"Missing or invalid {key}")
    if sha256_file(clean_path) != report["clean_sha256"]:
        raise ValueError("clean.tsv does not match its quality report")
    return report


def check_cluster(client: MongoClient) -> None:
    if client.admin.command("hello").get("msg") != "isdbgrid":
        raise ValueError("Connect to the mongos router")
    shards = client.admin.command("listShards")["shards"]
    if {shard["_id"] for shard in shards} != SHARDS:
        raise ValueError("The cluster must contain shard1 and shard2")
    metadata = client.config.collections.find_one({"_id": NAMESPACE})
    if (
        metadata is None
        or metadata.get("key") != {"user_id": "hashed"}
        or metadata.get("unique")
        or metadata.get("unsplittable")
    ):
        raise ValueError("gowalla.checkins must be sharded on the hashed user_id key")


def write_batch(collection, updates, first_row: int, last_row: int):
    try:
        result = collection.bulk_write(updates, ordered=False)
    except PyMongoError as error:
        raise RuntimeError(f"Batch at source lines {first_row}–{last_row}: {error}") from error
    if result.upserted_count + result.matched_count != len(updates):
        raise RuntimeError(f"Unexpected write count for source lines {first_row}–{last_row}")
    return result.upserted_count


def checkin_batches(clean_path: Path, expected: int, max_source_line: int):
    count = previous_row = batch_first = 0
    updates = []
    with clean_path.open(encoding="utf-8", newline="") as source:
        reader = csv.reader(source, delimiter="\t", strict=True)
        if tuple(next(reader, ())) != CLEAN_HEADER:
            raise ValueError("Unexpected clean.tsv header")
        for count, fields in enumerate(reader, 1):
            row_id, user_id, timestamp, latitude, longitude, location_id = fields
            row = parse_id(row_id)
            if not previous_row < row <= max_source_line or count > expected:
                raise ValueError(f"Unexpected source line or row count at clean.tsv record {count}")
            user = parse_id(user_id)
            lat, lon = parse_coords(latitude, longitude)
            if not updates:
                batch_first = row
            updates.append(
                UpdateOne(
                    {"user_id": user, "_id": row},
                    {"$setOnInsert": {
                        "ts": parse_utc(timestamp),
                        "loc": {"type": "Point", "coordinates": [lon, lat]},
                        "location_id": parse_id(location_id),
                    }},
                    upsert=True,
                    hint="_id_",
                )
            )
            previous_row = row
            if len(updates) == BATCH_SIZE:
                yield updates, batch_first, row
                updates = []

    if count != expected:
        raise ValueError(f"Expected {expected:,} clean records, read {count:,}")
    if updates:
        yield updates, batch_first, previous_row


def write_checkins(collection, clean_path: Path, expected: int, max_source_line: int) -> dict:
    start = perf_counter()
    pending = deque()
    count = inserted = 0
    with ThreadPoolExecutor(max_workers=WRITE_WORKERS) as pool:
        for updates, first_row, last_row in checkin_batches(clean_path, expected, max_source_line):
            future = pool.submit(write_batch, collection, updates, first_row, last_row)
            pending.append((future, len(updates)))
            if len(pending) == WRITE_WORKERS:
                finished, size = pending.popleft()
                inserted += finished.result()
                count += size
                if count % 100_000 == 0:
                    print(f"Written {count:,}/{expected:,} records ({inserted:,} new)", flush=True)
        for finished, size in pending:
            inserted += finished.result()
            count += size
    seconds = perf_counter() - start
    return {
        "processed": count,
        "inserted": inserted,
        "already_present": count - inserted,
        "write_seconds": round(seconds, 3),
        "rows_per_second": round(count / seconds, 1),
        "write_workers": WRITE_WORKERS,
    }


def verify_distribution(client: MongoClient, collection, expected: int) -> dict:
    total = collection.count_documents({})
    if total != expected:
        raise ValueError(f"Router count {total:,} differs from the clean count {expected:,}")
    pipeline = [{"$shardedDataDistribution": {}}, {"$match": {"ns": NAMESPACE}}]
    for attempt in range(13):
        distribution = next(client.admin.aggregate(pipeline), {})
        shards = distribution.get("shards", [])
        owned = {shard["shardName"]: shard["numOwnedDocuments"] for shard in shards}
        if (
            owned.keys() == SHARDS
            and min(owned.values()) > 0
            and sum(owned.values()) == total
            and all(shard["numOrphanedDocs"] == 0 for shard in shards)
        ):
            return owned
        if attempt < 12:
            sleep(5)
    raise ValueError(f"Shard counts did not reconcile: {distribution}")


def import_file(client: MongoClient, clean_path: Path, report: dict) -> dict:
    check_cluster(client)
    db = client[DATABASE]
    manifest = db.dataset
    collection = db.checkins
    version = {key: report[key] for key in ("input_sha256", "rule_version", "clean_sha256")}
    existing = manifest.find_one({"_id": MANIFEST_ID})
    if existing and existing["version"] != version:
        raise ValueError("Target collection belongs to a different data version")
    if not existing and collection.find_one({}, {"_id": 1}) is not None:
        raise ValueError("Target already contains data without an import manifest")
    if existing and existing["status"] == "ready":
        print("This version is already ready. Checking its current shard counts.", flush=True)
        return {
            **existing["import_metrics"],
            "current_shard_counts": verify_distribution(client, collection, report["clean_count"]),
        }

    manifest.replace_one(
        {"_id": MANIFEST_ID},
        {"_id": MANIFEST_ID, "version": version, "status": "loading"},
        upsert=True,
    )
    try:
        metrics = write_checkins(collection, clean_path, report["clean_count"], report["input_count"])
        index_start = perf_counter()
        print("Building trajectory and spatial indexes", flush=True)
        collection.create_index([("user_id", 1), ("ts", -1), ("_id", -1)], name="trajectory")
        collection.create_index([("loc", "2dsphere")], name="region")
        metrics["index_seconds"] = round(perf_counter() - index_start, 3)
        metrics["index_size_bytes"] = sum(
            item["storageStats"]["totalIndexSize"]
            for item in collection.aggregate([{"$collStats": {"storageStats": {}}}])
        )
        print("Verifying collection and shard counts", flush=True)
        shards = verify_distribution(client, collection, report["clean_count"])
        metrics["shard_counts"] = shards
        manifest.update_one(
            {"_id": MANIFEST_ID},
            {"$set": {
                "status": "ready",
                "quality_report": report,
                "shard_counts": shards,
                "import_metrics": metrics,
            }},
        )
    except (Exception, KeyboardInterrupt):
        try:
            manifest.update_one({"_id": MANIFEST_ID}, {"$set": {"status": "failed"}})
        except PyMongoError as error:
            print(f"Could not record import failure: {error}", file=sys.stderr)
        raise
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Import verified Gowalla check-ins into MongoDB")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--uri", default=DEFAULT_URI)
    args = parser.parse_args()
    global_lock = Path(tempfile.gettempdir()) / "gowalla-course-import.lock"
    try:
        with (
            FileLock(global_lock, timeout=0),
            FileLock(args.input.parent / ".pipeline.lock", timeout=0),
            MongoClient(args.uri, serverSelectionTimeoutMS=5000) as client,
        ):
            report = load_report(args.report, args.input)
            metrics = import_file(client, args.input, report)
    except (OSError, ValueError, RuntimeError, PyMongoError, Timeout) as error:
        print(f"Import failed: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Import interrupted", file=sys.stderr)
        return 130
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
