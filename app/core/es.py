# coding=utf-8
import os
from typing import List, Optional
from elasticsearch import AsyncElasticsearch

def _parse_hosts_from_env(value: Optional[str]) -> List[str]:
    if not value:
        return []
    parts = [p.strip() for p in value.split(",") if p.strip()]
    return parts

def normalize_es_host(host: str) -> str:
    h = (host or "").strip()
    if not h:
        return "http://localhost:9200"
    if "://" not in h:
        return f"http://{h}"
    return h

async def init_es(app):
    # 从环境变量读取 ES_HOSTS，未设置时默认本地 9200。
    hosts = _parse_hosts_from_env(os.getenv("ES_HOSTS")) or ["http://localhost:9200"]
    app.state.es = AsyncElasticsearch(
        hosts=hosts,
        verify_certs=False,
        ssl_show_warn=False,
    )

async def close_es(app):
    es = getattr(app.state, "es", None)
    if es is not None:
        await es.close()
