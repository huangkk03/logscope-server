# coding=utf-8
import os
import asyncio
import logging

LOG_DIR = "./logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)

def get_file_path(filename: str) -> str:
    return os.path.join(LOG_DIR, filename)

async def cleanup_file(path: str, delay: int = 120):
    await asyncio.sleep(delay)
    if os.path.exists(path):
        os.remove(path)
        logger.info(f"Cleanup removed {path}")
