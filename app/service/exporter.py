# coding=utf-8
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

async def export_logs(
    es,
    index: str,
    query: str,
    filters: list,
    file_path: str,
    max_size: int = 50000
) -> int:
    """
    Scroll 查询 ES 并写入文件
    """
    dsl = {
        "query": {
            "bool": {
                "must": [{"query_string": {"query": query}}],
                "filter": filters
            }
        },
        "_source": ["message"],
        "sort": [{"@timestamp": {"order": "asc"}}]
    }

    logger.info(f"ES DSL: {json.dumps(dsl, ensure_ascii=False)}")

    count = 0
    page_size = 2000
    scroll_id = None

    with open(file_path, "w", encoding="utf-8") as f:
        resp = await es.search(
            index=index,
            body=dsl,
            scroll="2m",
            size=page_size
        )
        scroll_id = resp.get("_scroll_id")

        try:
            while True:
                hits = resp["hits"]["hits"]
                if not hits:
                    break

                for h in hits:
                    f.write(h["_source"].get("message", "") + "\n")
                    count += 1
                    if count >= max_size:
                        break

                if count >= max_size:
                    break

                resp = await es.scroll(scroll_id=scroll_id, scroll="2m")
                scroll_id = resp.get("_scroll_id")
        finally:
            if scroll_id:
                await es.clear_scroll(scroll_id=scroll_id)

    return count
