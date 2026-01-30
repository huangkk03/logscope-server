# coding=utf-8
import uuid
from typing import Optional, Dict
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse, FileResponse
from pydantic import BaseModel, Field
from elasticsearch import AsyncElasticsearch

from app.core.auth import check_auth
from app.core.time import to_utc
from app.core.es import normalize_es_host
from app.service.exporter import export_logs
from app.storage.local import get_file_path, cleanup_file

router = APIRouter()

class SearchRequest(BaseModel):
    index: str
    es_host: Optional[str] = None
    es_api_key: Optional[str] = None
    query: str = "*"
    # pydantic v2：Optional 但未给默认值时仍然视为必填；这里显式给 None，避免 422
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    size: int = Field(default=50000, ge=1, le=200000)
    filters: Optional[Dict[str, str]] = None


@router.post("/search")
async def search(
    req: Request,
    body: SearchRequest,
    background_tasks: BackgroundTasks
):
    check_auth(req)

    # 不要修改全局共享的 app.state.es（并发请求会互相覆盖 hosts/api_key）。
    # 每次请求按参数创建独立 ES 客户端，用完即关闭。
    kwargs = dict(
        hosts=[normalize_es_host(body.es_host)],
        verify_certs=False,
        ssl_show_warn=False,
    )
    if body.es_api_key:
        kwargs["api_key"] = body.es_api_key

    es = AsyncElasticsearch(**kwargs)

    filters = []

    # 时间过滤优化：
    # - 只要传了 start_time/end_time 任意一个就生效（不强制两个都传）
    # - 若两者都不传：默认从“北京时间当天 00:00:00”开始往后取
    if body.start_time or body.end_time:
        ts_range = {}
        if body.start_time:
            ts_range["gte"] = to_utc(body.start_time)
        if body.end_time:
            ts_range["lte"] = to_utc(body.end_time)
        filters.append({"range": {"@timestamp": ts_range}})
    else:
        bj_tz = timezone(timedelta(hours=8))
        start_of_today_bj = datetime.now(bj_tz).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        filters.append({
            "range": {
                "@timestamp": {
                    "gte": to_utc(start_of_today_bj.isoformat())
                }
            }
        })

    if body.filters:
        for k, v in body.filters.items():
            if v:
                filters.append({"match_phrase": {k: v}})

    file_name = f"log_{uuid.uuid4().hex}.txt"
    file_path = get_file_path(file_name)

    try:
        count = await export_logs(
            es=es,
            index=body.index,
            query=body.query,
            filters=filters,
            file_path=file_path,
            max_size=body.size
        )
    finally:
        await es.close()

    if count == 0:
        raise HTTPException(404, "No log found")

    base = str(req.base_url).rstrip("/")
    url = f"{base}/api/logscope/download/{file_name}"

    background_tasks.add_task(cleanup_file, file_path, 120)

    return PlainTextResponse(url)


@router.get("/download/{file}")
async def download(file: str, req: Request):
    check_auth(req)
    path = get_file_path(file)
    return FileResponse(path, filename=file)


@router.get("/preview/{file}")
async def preview(file: str, req: Request, max_bytes: int = 200_000):
    """
    在线预览：只读取文件前 max_bytes（默认 200KB），避免浏览器直接加载大文件一直转圈。
    """
    check_auth(req)
    path = get_file_path(file)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_bytes)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    return PlainTextResponse(content)
