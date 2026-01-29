# coding=utf-8
from datetime import datetime, timedelta

def to_utc(time_str: str) -> str:
    """
    北京时间 ISO8601 → UTC ISO8601
    """
    dt = datetime.fromisoformat(time_str.replace("Z", ""))
    return (dt - timedelta(hours=8)).isoformat()
