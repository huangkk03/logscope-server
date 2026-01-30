# coding=utf-8
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parent.parent.parent  # .../logscope-server
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "config.db"


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS es_configs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE,
              host TEXT NOT NULL,
              api_key TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        # Filters 选项（最终形态）：一条记录 = 一个 key + 多个可选 values
        # - 新表：filter_options(key UNIQUE, values_json)
        # - 迁移：尝试从旧 filter_presets/items_json（或更老的 filters_json/value）聚合导入
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS filter_options (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              key TEXT NOT NULL UNIQUE,
              label TEXT NOT NULL DEFAULT '', -- 中文别名（展示用）
              values_json TEXT NOT NULL, -- JSON array: ["v1","v2",...]
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        # 旧库升级：补 label 列
        cols2 = [r["name"] for r in conn.execute("PRAGMA table_info(filter_options)").fetchall()]
        if "label" not in cols2:
            conn.execute("ALTER TABLE filter_options ADD COLUMN label TEXT NOT NULL DEFAULT '';")
            conn.execute("UPDATE filter_options SET label = key WHERE label = '' OR label IS NULL;")

        # 若新表为空，则尝试从旧表迁移（只做一次）
        cnt = conn.execute("SELECT COUNT(1) FROM filter_options").fetchone()[0]
        if int(cnt) == 0:
            old_cols = [r["name"] for r in conn.execute("PRAGMA table_info(filter_presets)").fetchall()]
            if old_cols:
                key_to_vals: Dict[str, set] = {}
                # 优先读 items_json（新版 preset）
                if "items_json" in old_cols:
                    rows = conn.execute("SELECT items_json FROM filter_presets").fetchall()
                    for r in rows:
                        try:
                            items = json.loads(r["items_json"] or "[]")
                        except Exception:
                            items = []
                        if not isinstance(items, list):
                            continue
                        for it in items:
                            if not isinstance(it, dict):
                                continue
                            k = str(it.get("key") or "").strip()
                            vals = it.get("values")
                            if not k:
                                continue
                            if isinstance(vals, list):
                                vs = [str(x).strip() for x in vals if str(x).strip()]
                            else:
                                sv = str(vals or "").strip()
                                vs = [sv] if sv else []
                            if not vs:
                                continue
                            s = key_to_vals.setdefault(k, set())
                            for v in vs:
                                s.add(v)
                # 更老的 filters_json
                if "filters_json" in old_cols:
                    rows = conn.execute("SELECT filters_json FROM filter_presets").fetchall()
                    for r in rows:
                        raw = (r["filters_json"] or "").strip()
                        try:
                            obj = json.loads(raw) if raw else {}
                        except Exception:
                            obj = {}
                        if not isinstance(obj, dict):
                            continue
                        for k, v in obj.items():
                            kk = str(k).strip()
                            vv = str(v).strip()
                            if kk and vv:
                                key_to_vals.setdefault(kk, set()).add(vv)
                # 更老的 value（多行 key=value）
                if "value" in old_cols:
                    rows = conn.execute("SELECT value FROM filter_presets").fetchall()
                    for r in rows:
                        raw = (r["value"] or "").strip()
                        for line in raw.splitlines():
                            s = line.strip()
                            if not s or s.startswith("#"):
                                continue
                            if "=" in s:
                                k, v = s.split("=", 1)
                            elif ":" in s:
                                k, v = s.split(":", 1)
                            else:
                                k, v = "container.labels.service_project", s
                            kk = k.strip()
                            vv = v.strip()
                            if not (kk and vv):
                                continue
                            for part in [x.strip() for x in vv.split(",") if x.strip()]:
                                key_to_vals.setdefault(kk, set()).add(part)

                for k, vs in key_to_vals.items():
                    conn.execute(
                        "INSERT INTO filter_options (key, values_json) VALUES (?, ?)",
                        (k, json.dumps(sorted(vs), ensure_ascii=False)),
                    )

        conn.commit()
    finally:
        conn.close()


# ---------- ES configs ----------
def list_es_configs() -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, name, host, created_at, updated_at FROM es_configs ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_es_config(es_config_id: int) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, name, host, api_key, created_at, updated_at FROM es_configs WHERE id = ?",
            (es_config_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _get_es_config_id_by_name(name: str) -> Optional[int]:
    conn = _connect()
    try:
        row = conn.execute("SELECT id FROM es_configs WHERE name = ?", (name,)).fetchone()
        return int(row["id"]) if row else None
    finally:
        conn.close()


def upsert_es_config(*, name: str, host: str, api_key: str, es_config_id: Optional[int] = None) -> Dict[str, Any]:
    conn = _connect()
    try:
        if es_config_id is None:
            try:
                conn.execute(
                    "INSERT INTO es_configs (name, host, api_key) VALUES (?, ?, ?)",
                    (name, host, api_key),
                )
                conn.commit()
                new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                return get_es_config(int(new_id))  # type: ignore[arg-type]
            except sqlite3.IntegrityError:
                # name 唯一：如果已存在则自动更新（更贴合“保存”语义）
                existing_id = _get_es_config_id_by_name(name)
                if existing_id is None:
                    raise
                es_config_id = existing_id

        conn.execute(
            """
            UPDATE es_configs
               SET name = ?, host = ?, api_key = ?, updated_at = datetime('now')
             WHERE id = ?
            """,
            (name, host, api_key, es_config_id),
        )
        conn.commit()
        cfg = get_es_config(es_config_id)
        if cfg is None:
            raise KeyError("ES config not found")
        return cfg
    finally:
        conn.close()


def delete_es_config(es_config_id: int) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM es_configs WHERE id = ?", (es_config_id,))
        conn.commit()
    finally:
        conn.close()


# ---------- Filter options (key -> values[]) ----------
def list_filter_presets() -> List[Dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, key, label, created_at, updated_at FROM filter_options ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_filter_options_full() -> List[Dict[str, Any]]:
    """一次性返回所有 filter key/label/values，避免前端 N+1 请求造成卡顿。"""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, key, label, values_json, created_at, updated_at FROM filter_options ORDER BY id DESC"
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            try:
                d["values"] = json.loads(d.pop("values_json") or "[]")
            except Exception:
                d["values"] = []
                d.pop("values_json", None)
            out.append(d)
        return out
    finally:
        conn.close()


def get_filter_preset(preset_id: int) -> Optional[Dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, key, label, values_json, created_at, updated_at FROM filter_options WHERE id = ?",
            (preset_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["values"] = json.loads(d.pop("values_json") or "[]")
        except Exception:
            d["values"] = []
            d.pop("values_json", None)
        return d
    finally:
        conn.close()


def _get_filter_preset_id_by_name(name: str) -> Optional[int]:
    conn = _connect()
    try:
        row = conn.execute("SELECT id FROM filter_options WHERE key = ?", (name,)).fetchone()
        return int(row["id"]) if row else None
    finally:
        conn.close()


def upsert_filter_preset(*, name: str, items: List[Dict[str, Any]], preset_id: Optional[int] = None) -> Dict[str, Any]:
    conn = _connect()
    try:
        # 兼容调用：name 视为 key；items 里取第一个匹配 key 的 values，否则当成 values 列表
        key = (name or "").strip()
        label = key
        values: List[str] = []
        if isinstance(items, list) and items:
            # 允许传 [{key, values}] 或直接传 ["a","b"]
            if isinstance(items[0], dict):
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    k = str(it.get("key") or "").strip()
                    if k and key and k != key:
                        continue
                    vals = it.get("values") or []
                    if isinstance(vals, list):
                        values.extend([str(x).strip() for x in vals if str(x).strip()])
            else:
                values.extend([str(x).strip() for x in items if str(x).strip()])
        values = sorted(set(values))
        values_json = json.dumps(values, ensure_ascii=False)
        if preset_id is None:
            try:
                conn.execute(
                    "INSERT INTO filter_options (key, label, values_json) VALUES (?, ?, ?)",
                    (key, label, values_json),
                )
                conn.commit()
                new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                res = get_filter_preset(int(new_id))  # type: ignore[arg-type]
                if res is None:
                    raise RuntimeError("Failed to create preset")
                return res
            except sqlite3.IntegrityError:
                # name 唯一：如果已存在则自动更新
                existing_id = _get_filter_preset_id_by_name(key)
                if existing_id is None:
                    raise
                preset_id = existing_id

        conn.execute(
            """
            UPDATE filter_options
               SET key = ?, label = COALESCE(NULLIF(label,''), ?), values_json = ?, updated_at = datetime('now')
             WHERE id = ?
            """,
            (key, key, values_json, preset_id),
        )
        conn.commit()
        res = get_filter_preset(preset_id)
        if res is None:
            raise KeyError("Preset not found")
        return res
    finally:
        conn.close()


def delete_filter_preset(preset_id: int) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM filter_options WHERE id = ?", (preset_id,))
        conn.commit()
    finally:
        conn.close()


