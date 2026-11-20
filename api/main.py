import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from pymongo.errors import ExecutionTimeout, PyMongoError

from api.routes import router
from db.import_checkins import DATABASE, DEFAULT_URI

WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    uri = os.environ.get("GOWALLA_MONGO_URI", DEFAULT_URI)
    with MongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=3000) as client:
        app.state.database = client[DATABASE]
        yield


app = FastAPI(title="Gowalla 签到数据服务", version="1.0.0", lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=WEB_ROOT / "static"), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(WEB_ROOT / "index.html")


@app.exception_handler(ExecutionTimeout)
async def query_timeout(request: Request, error: ExecutionTimeout):
    return JSONResponse(status_code=504, content={"detail": "查询超时，请缩小空间或时间范围"})


@app.exception_handler(PyMongoError)
async def database_error(request: Request, error: PyMongoError):
    logger.warning("Database request failed at %s: %s", request.url.path, type(error).__name__)
    return JSONResponse(status_code=503, content={"detail": "数据库暂时不可用"})
