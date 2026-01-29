# coding=utf-8
import re
from datetime import datetime, timedelta, timezone

# Python 3.6 没有 datetime.fromisoformat，需要自己解析常见 ISO8601 变体：
# - 2026-01-28T17:03:17
# - 2026-01-28T17:03:17.123
# - 2026-01-28T17:03:17Z
# - 2026-01-28T17:03:17+08:00 / +0800
_TZ_RE = re.compile(r"([+-])(\d{2}):?(\d{2})$")

def _parse_iso8601(s: str) -> datetime:
    s = (s or "").strip()
    if not s:
        raise ValueError("empty time string")

    tzinfo = None

    if s.endswith(("Z", "z")):
        tzinfo = timezone.utc
        s = s[:-1]
    else:
        m = _TZ_RE.search(s)
        if m:
            sign, hh, mm = m.group(1), int(m.group(2)), int(m.group(3))
            delta = timedelta(hours=hh, minutes=mm)
            if sign == "-":
                delta = -delta
            tzinfo = timezone(delta)
            s = s[: m.start()]

    # 处理小数秒
    micro = 0
    if "." in s:
        base, frac = s.split(".", 1)
        # frac 里可能还有空白，或者被截断，最多取 6 位
        frac = re.sub(r"\s+", "", frac)
        frac_digits = "".join(ch for ch in frac if ch.isdigit())
        if frac_digits:
            micro = int((frac_digits[:6]).ljust(6, "0"))
        s = base

    dt = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S").replace(microsecond=micro)
    if tzinfo is not None:
        dt = dt.replace(tzinfo=tzinfo)
    return dt

def to_utc(time_str: str) -> str:
    """
    将输入时间转换为 UTC ISO8601。

    约定：
    - 若输入带时区（如 `Z` / `+08:00` / `+00:00`），按其时区换算到 UTC。
    - 若输入不带时区（naive），默认按北京时间（UTC+8）理解，再换算到 UTC。
    """
    s = (time_str or "").strip()
    if not s:
        return s

    dt = _parse_iso8601(s)

    if dt.tzinfo is not None:
        # 转为 UTC，再去掉 tzinfo（ES 通常接受无 tz 的 ISO8601）
        return dt.astimezone(timezone.utc).replace(tzinfo=None).isoformat()

    # naive 时间：按北京时间（UTC+8）处理
    return (dt - timedelta(hours=8)).isoformat()
