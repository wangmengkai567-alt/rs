import base64
import binascii
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from bson import MaxKey, MinKey
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from cleaner.schema import MAX_INT64, parse_utc

router = APIRouter(prefix="/api")
ORDER = {"ts": -1, "_id": -1}
QUERY_TIMEOUT_MS = 15_000


def database(request: Request):
    return request.app.state.database


Database = Annotated[object, Depends(database)]


def get_ready_dataset(db) -> dict:
    dataset = db.dataset.find_one({"_id": "current", "status": "ready"})
    if dataset is None:
        raise HTTPException(503, "数据尚未完成导入和验收")
    return dataset


@router.get("/health")
def health(db: Database):
    try:
        db.command("ping")
        dataset = db.dataset.find_one({"_id": "current"}, {"status": 1, "_id": 0})
    except PyMongoError:
        return JSONResponse(
            {"database": "unavailable", "dataset": "unavailable"}, status_code=503
        )
    state = dataset["status"] if dataset else "not_loaded"
    return JSONResponse(
        {"database": "connected", "dataset": state}, status_code=200 if state == "ready" else 503
    )


@router.get("/stats/overview")
def overview(db: Database):
    dataset = get_ready_dataset(db)
    quality = dataset["quality_report"]
    keys = (
        "input_count", "clean_count", "reject_count", "user_count", "location_count",
        "first_ts_utc", "last_ts_utc",
    )
    return {
        **{key: quality[key] for key in keys},
        "version": dataset["version"],
        "shard_counts": dataset["shard_counts"],
    }


@router.get("/quality")
def quality_report(db: Database):
    return get_ready_dataset(db)["quality_report"]


@dataclass(frozen=True)
class Page:
    start: datetime | None
    end: datetime | None
    limit: int
    cursor: str | None


def page_options(
    start: Annotated[str | None, Query(max_length=20)] = None,
    end: Annotated[str | None, Query(max_length=20)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    cursor: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> Page:
    try:
        first = parse_utc(start) if start is not None else None
        last = parse_utc(end) if end is not None else None
    except ValueError as error:
        raise HTTPException(422, "时间必须为 YYYY-MM-DDTHH:MM:SSZ 格式") from error
    if first is not None and last is not None and first >= last:
        raise HTTPException(422, "开始时间必须早于结束时间")
    return Page(first, last, limit, cursor)


PageOptions = Annotated[Page, Depends(page_options)]


def parse_bbox(bbox: str) -> list[float]:
    try:
        west, south, east, north = map(float, bbox.split(","))
    except ValueError as error:
        raise HTTPException(422, "请按西、南、东、北顺序提供四个坐标") from error
    if not (-180 <= west < east <= 180 and east - west < 180 and -90 < south < north < 90):
        raise HTTPException(422, "区域坐标超出范围、顺序有误或经度跨度达到 180°")
    return [west, south, east, north]


def format_utc(timestamp: datetime | None) -> str | None:
    return timestamp.isoformat().replace("+00:00", "Z") if timestamp is not None else None


def decode_cursor(token: str, scope: str) -> tuple[datetime, int]:
    try:
        encoded = token + "=" * (-len(token) % 4)
        payload = json.loads(base64.b64decode(encoded, altchars=b"-_", validate=True))
        if not isinstance(payload, list) or len(payload) != 3:
            raise ValueError
        signature, timestamp, row = payload
        if signature != scope or type(row) is not int or not 0 < row <= MAX_INT64:
            raise ValueError
        if not isinstance(timestamp, str):
            raise ValueError
        return parse_utc(timestamp), row
    except (ValueError, binascii.Error) as error:
        raise HTTPException(422, "分页游标无效或与当前查询条件不匹配") from error


def encode_cursor(scope: str, document: dict) -> str:
    payload = json.dumps([scope, format_utc(document["ts"]), document["_id"]], separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("ascii")).decode("ascii").rstrip("=")


def read_shard_chunks(collection, session) -> list[dict]:
    config = collection.database.client.config
    metadata = config.collections.find_one(
        {"_id": collection.full_name, "key": {"user_id": "hashed"}}, {"uuid": 1},
        session=session, max_time_ms=QUERY_TIMEOUT_MS,
    )
    if metadata is None:
        raise HTTPException(503, "签到集合的分片元数据不可用")
    return list(config.chunks.find(
        {"uuid": metadata["uuid"]}, {"min": 1, "max": 1, "shard": 1, "_id": 0},
        session=session, max_time_ms=QUERY_TIMEOUT_MS,
    ))


def shard_for_hash(user_hash: int, chunks: list[dict]) -> str:
    for chunk in chunks:
        lower, upper = chunk["min"]["user_id"], chunk["max"]["user_id"]
        if (isinstance(lower, MinKey) or lower <= user_hash) and (
            isinstance(upper, MaxKey) or user_hash < upper
        ):
            return chunk["shard"]
    raise HTTPException(503, "无法确定签到记录所属分片")


def find_page(db: Database, page: Page, selector: dict, criteria: dict) -> dict:
    dataset = get_ready_dataset(db)
    boundaries = {"$gte": page.start, "$lt": page.end}
    time_filter = {key: value for key, value in boundaries.items() if value is not None}
    if time_filter:
        selector["ts"] = time_filter

    scope_data = [dataset["version"], criteria, format_utc(page.start), format_utc(page.end)]
    scope = hashlib.sha256(json.dumps(scope_data, sort_keys=True).encode("ascii")).hexdigest()
    if page.cursor is not None:
        timestamp, row = decode_cursor(page.cursor, scope)
        selector["$or"] = [{"ts": {"$lt": timestamp}}, {"ts": timestamp, "_id": {"$lt": row}}]

    collection = db.checkins
    pipeline = [
        {"$match": selector},
        {"$sort": ORDER},
        {"$limit": page.limit + 1},
        {"$project": {
            "_id": 1, "user_id": 1, "ts": 1, "loc.coordinates": 1, "location_id": 1,
            "user_hash": {"$toHashedIndexKey": "$user_id"},
        }},
    ]
    # Read the documents and chunk ownership at the same point in time during migrations.
    with db.client.start_session(snapshot=True) as session:
        documents = list(collection.aggregate(pipeline, session=session, maxTimeMS=QUERY_TIMEOUT_MS))
        visible = documents[:page.limit]
        chunks = read_shard_chunks(collection, session) if visible else []

    return {
        "items": [
            {
                "source_line": row["_id"],
                "user_id": row["user_id"],
                "ts_utc": format_utc(row["ts"]),
                "coordinates": row["loc"]["coordinates"],
                "location_id": row["location_id"],
                "shard": shard_for_hash(row["user_hash"], chunks),
            }
            for row in visible
        ],
        "next_cursor": encode_cursor(scope, visible[-1]) if len(documents) > page.limit else None,
    }


@router.get("/users/{user_id}/trajectory")
def trajectory(user_id: Annotated[int, Path(ge=0, le=MAX_INT64)], page: PageOptions, db: Database):
    return find_page(db, page, {"user_id": user_id}, {"user_id": user_id})


@router.get("/checkins/geo")
def region(bbox: Annotated[str, Query(max_length=128)], page: PageOptions, db: Database):
    west, south, east, north = parse_bbox(bbox)
    ring = [[west, south], [east, south], [east, north], [west, north], [west, south]]
    geometry = {"type": "Polygon", "coordinates": [ring]}
    return find_page(
        db, page, {"loc": {"$geoWithin": {"$geometry": geometry}}},
        {"bbox": [west, south, east, north]},
    )
