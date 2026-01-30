# coding=utf-8
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse, FileResponse
from pydantic import BaseModel, Field
from elasticsearch import AsyncElasticsearch

from app.core.auth import check_auth
from app.core.time import to_utc
from app.core.es import normalize_es_host
from app.storage.config_db import get_es_config, get_filter_preset
from app.service.exporter import export_logs
from app.storage.local import get_file_path, cleanup_file

router = APIRouter()

async def _pick_agg_field(es: AsyncElasticsearch, index: str, field: str) -> str:
    """
    为 terms 聚合选择可聚合的字段：
    - 优先使用 field 本身
    - 不行则尝试 field.keyword
    """
    candidates = []
    f = (field or "").strip()
    if not f:
        return f
    candidates.append(f)
    if not f.endswith(".keyword"):
        candidates.append(f + ".keyword")

    try:
        resp = await es.field_caps(index=index, fields=candidates)
        fields = (resp or {}).get("fields") or {}
        for cand in candidates:
            info = fields.get(cand) or {}
            for _, meta in info.items():
                if meta.get("aggregatable") is True:
                    return cand
    except Exception:
        pass

    # fallback
    return candidates[-1]


class SearchRequest(BaseModel):
    index: str
    # 后台预配置（推荐）：只传 id，服务端读取 host/api_key，避免前端暴露密钥
    es_config_id: Optional[int] = None
    es_host: Optional[str] = None
    es_api_key: Optional[str] = None
    query: str = "*"
    # pydantic v2：Optional 但未给默认值时仍然视为必填；这里显式给 None，避免 422
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    size: int = Field(default=50000, ge=1, le=200000)
    filter_preset_id: Optional[int] = None
    # filters 支持：
    # - {"k": "v"}  单值
    # - {"k": ["v1","v2"]}  多值（OR）
    filters: Optional[Dict[str, Any]] = None


@router.post("/search")
async def search(
    req: Request,
    body: SearchRequest,
    background_tasks: BackgroundTasks
):
    check_auth(req)

    # 解析 ES 连接信息：优先使用后台预配置
    es_host = body.es_host
    es_api_key = body.es_api_key
    if body.es_config_id is not None:
        cfg = get_es_config(body.es_config_id)
        if not cfg:
            raise HTTPException(400, "Invalid es_config_id")
        es_host = cfg.get("host") or es_host
        es_api_key = cfg.get("api_key") or es_api_key

    # 不要修改全局共享的 app.state.es（并发请求会互相覆盖 hosts/api_key）。
    # 每次请求按参数创建独立 ES 客户端，用完即关闭。
    kwargs = dict(
        hosts=[normalize_es_host(es_host)],
        verify_certs=False,
        ssl_show_warn=False,
    )
    if es_api_key:
        kwargs["api_key"] = es_api_key

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

    # filters preset（后台配置：key + values[]）
    preset_filters: Dict[str, Any] = {}
    if body.filter_preset_id is not None:
        p = get_filter_preset(body.filter_preset_id)
        if not p:
            raise HTTPException(400, "Invalid filter_preset_id")
        k = str(p.get("key") or "").strip()
        vals = p.get("values") or []
        if k and isinstance(vals, list):
            vlist = [str(x).strip() for x in vals if str(x).strip()]
            if vlist:
                preset_filters[k] = vlist

    # 合并：preset 作为默认值，body.filters 可覆盖/补充
    merged_filters: Dict[str, Any] = {}
    for k, v in (preset_filters or {}).items():
        if v:
            merged_filters[k] = v
    if body.filters:
        for k, v in body.filters.items():
            if v:
                merged_filters[k] = v

    for k, v in merged_filters.items():
        if not v:
            continue
        # 多值：OR
        if isinstance(v, list):
            should = [{"match_phrase": {k: vv}} for vv in v if vv]
            if should:
                filters.append({"bool": {"should": should, "minimum_should_match": 1}})
            continue
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


class SuggestValuesRequest(BaseModel):
    index: str
    es_config_id: Optional[int] = None
    es_host: Optional[str] = None
    es_api_key: Optional[str] = None
    field: str = Field(min_length=1, max_length=300)
    query: str = "*"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None  # 其它过滤条件
    size: int = Field(default=200, ge=1, le=1000)


@router.post("/suggest-values")
async def suggest_values(req: Request, body: SuggestValuesRequest):
    """
    给前端下拉选项用：从 ES 动态取某个字段的候选值（terms 聚合）。
    目前主要用于 container.name 这类枚举值较多、变化频繁的字段。
    """
    check_auth(req)

    # 解析 ES 连接信息：优先使用后台预配置
    es_host = body.es_host
    es_api_key = body.es_api_key
    if body.es_config_id is not None:
        cfg = get_es_config(body.es_config_id)
        if not cfg:
            raise HTTPException(400, "Invalid es_config_id")
        es_host = cfg.get("host") or es_host
        es_api_key = cfg.get("api_key") or es_api_key

    kwargs = dict(
        hosts=[normalize_es_host(es_host)],
        verify_certs=False,
        ssl_show_warn=False,
    )
    if es_api_key:
        kwargs["api_key"] = es_api_key
    es = AsyncElasticsearch(**kwargs)

    try:
        filters = []

        # 时间范围（与 search 一致）
        if body.start_time or body.end_time:
            ts_range = {}
            if body.start_time:
                ts_range["gte"] = to_utc(body.start_time)
            if body.end_time:
                ts_range["lte"] = to_utc(body.end_time)
            filters.append({"range": {"@timestamp": ts_range}})
        else:
            bj_tz = timezone(timedelta(hours=8))
            start_of_today_bj = datetime.now(bj_tz).replace(hour=0, minute=0, second=0, microsecond=0)
            filters.append({"range": {"@timestamp": {"gte": to_utc(start_of_today_bj.isoformat())}}})

        # 其它过滤条件（支持单值/多值）
        if body.filters:
            for k, v in body.filters.items():
                if not v:
                    continue
                if isinstance(v, list):
                    should = [{"match_phrase": {k: vv}} for vv in v if vv]
                    if should:
                        filters.append({"bool": {"should": should, "minimum_should_match": 1}})
                else:
                    filters.append({"match_phrase": {k: v}})

        agg_field = await _pick_agg_field(es, body.index, body.field)

        dsl = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [{"query_string": {"query": body.query or "*"}}],
                    "filter": filters,
                }
            },
            "aggs": {
                "vals": {
                    "terms": {
                        "field": agg_field,
                        "size": body.size,
                        "order": {"_count": "desc"},
                    }
                }
            },
        }

        resp = await es.search(index=body.index, body=dsl)
        buckets = (((resp or {}).get("aggregations") or {}).get("vals") or {}).get("buckets") or []
        values = []
        for b in buckets:
            key = b.get("key")
            if key is None:
                continue
            s = str(key).strip()
            if s:
                values.append(s)
        return {"field": body.field, "agg_field": agg_field, "values": values}
    finally:
        await es.close()


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
