# coding=utf-8
from typing import List, Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import check_auth
from app.storage.config_db import (
    list_es_configs,
    get_es_config,
    upsert_es_config,
    delete_es_config,
    list_filter_presets,
    list_filter_options_full,
    get_filter_preset,
    upsert_filter_preset,
    delete_filter_preset,
)

router = APIRouter()


class ESConfigUpsert(BaseModel):
    id: Optional[int] = None
    name: str = Field(min_length=1, max_length=80)
    host: str = Field(min_length=1, max_length=300)
    api_key: str = Field(min_length=1, max_length=5000)


class FilterPresetUpsert(BaseModel):
    id: Optional[int] = None
    # 直接对应前台的 filters 行：key + 多个可选 values
    key: str = Field(min_length=1, max_length=200)
    label: str = Field(default="", max_length=200)
    values: List[str] = Field(default_factory=list)


@router.get("/es-configs")
async def api_list_es_configs(req: Request):
    check_auth(req)
    return list_es_configs()


@router.get("/es-configs/{es_config_id}")
async def api_get_es_config(es_config_id: int, req: Request):
    check_auth(req)
    cfg = get_es_config(es_config_id)
    if not cfg:
        raise HTTPException(404, "Not found")
    # 不把 api_key 直接回显给列表页以外的场景（这里仍返回，便于编辑）
    return cfg


@router.post("/es-configs")
async def api_upsert_es_config(req: Request, body: ESConfigUpsert):
    check_auth(req)
    try:
        return upsert_es_config(
            es_config_id=body.id,
            name=body.name,
            host=body.host,
            api_key=body.api_key,
        )
    except Exception as e:
        raise HTTPException(400, str(e))


@router.delete("/es-configs/{es_config_id}")
async def api_delete_es_config(es_config_id: int, req: Request):
    check_auth(req)
    delete_es_config(es_config_id)
    return {"ok": True}


@router.get("/filter-presets")
async def api_list_filter_presets(req: Request):
    check_auth(req)
    return list_filter_presets()


@router.get("/filter-options")
async def api_list_filter_options_full(req: Request):
    """给控制台用：一次性返回 key/label/values，避免前端多次请求。"""
    check_auth(req)
    return list_filter_options_full()


@router.get("/filter-presets/{preset_id}")
async def api_get_filter_preset(preset_id: int, req: Request):
    check_auth(req)
    p = get_filter_preset(preset_id)
    if not p:
        raise HTTPException(404, "Not found")
    return p


@router.post("/filter-presets")
async def api_upsert_filter_preset(req: Request, body: FilterPresetUpsert):
    check_auth(req)
    try:
        # 复用存储层 upsert_filter_preset(name, items) 的兼容签名：name=key，items=[values...]
        # 兼容存储层签名：name=key，items=values
        res = upsert_filter_preset(
            preset_id=body.id,
            name=body.key,
            items=body.values,
        )
        # 若提供 label，则单独更新（存储层默认 label=key）
        if body.label:
            from app.storage.config_db import _connect
            conn = _connect()
            try:
                conn.execute(
                    "UPDATE filter_options SET label = ?, updated_at = datetime('now') WHERE id = ?",
                    (body.label.strip(), res["id"]),
                )
                conn.commit()
            finally:
                conn.close()
            res = get_filter_preset(res["id"]) or res
        return res
    except Exception as e:
        raise HTTPException(400, str(e))


@router.delete("/filter-presets/{preset_id}")
async def api_delete_filter_preset(preset_id: int, req: Request):
    check_auth(req)
    delete_filter_preset(preset_id)
    return {"ok": True}


