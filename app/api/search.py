# coding=utf-8
import uuid
from typing import Optional, Dict
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

    if body.start_time and body.end_time:
        filters.append({
            "range": {
                "@timestamp": {
                    "gte": to_utc(body.start_time),
                    "lte": to_utc(body.end_time)
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
