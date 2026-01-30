# coding=utf-8
import os
from pathlib import Path
import asyncio
import logging

# 使用绝对路径，避免 uvicorn --reload / 不同工作目录导致找不到导出文件
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # .../logscope-server
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)

def get_file_path(filename: str) -> str:
    return str(LOG_DIR / filename)

async def cleanup_file(path: str, delay: int = 120):
    await asyncio.sleep(delay)
    if os.path.exists(path):
        os.remove(path)
        logger.info(f"Cleanup removed {path}")
