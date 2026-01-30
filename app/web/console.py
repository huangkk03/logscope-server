# coding=utf-8
import json
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

_LS_KEY = "logscope.console.v1"

@router.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/console")


@router.get("/console", response_class=HTMLResponse, include_in_schema=False)
async def console():
    # 纯静态 HTML + 原生 JS（不引入额外依赖），同域调用 /api/logscope/search
    html = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LogScope 控制台</title>
  <style>
    :root {
      --bg: #0b1220;
      --panel: #121a2b;
      --muted: #93a4c7;
      --text: #e8eefc;
      --border: rgba(255,255,255,0.10);
      --accent: #4f8cff;
      --danger: #ff5a7a;
      --ok: #3ddc97;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
      background: radial-gradient(1200px 600px at 20% -10%, rgba(79,140,255,0.22), transparent 55%),
                  radial-gradient(900px 500px at 110% 10%, rgba(61,220,151,0.16), transparent 50%),
                  var(--bg);
      color: var(--text);
    }
    .wrap { max-width: 1100px; margin: 28px auto; padding: 0 18px; }
    .top {
      display: flex; align-items: flex-end; justify-content: space-between; gap: 12px;
      margin-bottom: 14px;
    }
    h1 { font-size: 20px; margin: 0; letter-spacing: 0.2px; }
    .sub { color: var(--muted); font-size: 12px; margin-top: 6px; }
    .grid { display: grid; grid-template-columns: 1fr; gap: 12px; }
    .card {
      background: rgba(18,26,43,0.72);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      backdrop-filter: blur(10px);
    }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .row3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
    label { display: block; font-size: 12px; color: var(--muted); margin: 6px 0; }
    input, textarea, select {
      width: 100%;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: rgba(10,16,28,0.55);
      color: var(--text);
      padding: 10px 10px;
      outline: none;
    }
    textarea { min-height: 70px; resize: vertical; }
    input:focus, textarea:focus, select:focus { border-color: rgba(79,140,255,0.55); box-shadow: 0 0 0 3px rgba(79,140,255,0.12); }
    .actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    button {
      border: 1px solid rgba(79,140,255,0.55);
      background: linear-gradient(180deg, rgba(79,140,255,0.35), rgba(79,140,255,0.16));
      color: var(--text);
      padding: 10px 12px;
      border-radius: 10px;
      cursor: pointer;
    }
    button.secondary {
      border-color: var(--border);
      background: rgba(10,16,28,0.35);
      color: var(--muted);
    }
    button.danger {
      border-color: rgba(255,90,122,0.55);
      background: linear-gradient(180deg, rgba(255,90,122,0.28), rgba(255,90,122,0.12));
    }
    .hint { color: var(--muted); font-size: 12px; }
    .filters { width: 100%; border-collapse: collapse; margin-top: 6px; }
    .filters th, .filters td { border-bottom: 1px solid var(--border); padding: 8px 6px; font-size: 12px; }
    .filters th { text-align: left; color: var(--muted); font-weight: 600; }
    .tag {
      display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px;
      border: 1px solid var(--border); color: var(--muted); background: rgba(10,16,28,0.35);
    }
    .status.ok { color: var(--ok); }
    .status.bad { color: var(--danger); }
    pre {
      margin: 0; padding: 12px; border-radius: 12px; overflow: auto;
      border: 1px solid var(--border);
      background: rgba(10,16,28,0.55);
      color: #d7e3ff;
      font-size: 12px;
      line-height: 1.45;
    }
    a { color: var(--accent); }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    .mini-actions { display:flex; gap:8px; flex-wrap: wrap; }

    /* 时间选择：右下角 Popover（类似 Kibana） */
    .popover {
      position: fixed;
      right: 18px;
      bottom: 18px;
      width: min(520px, calc(100vw - 24px));
      border: 1px solid var(--border);
      border-radius: 14px;
      background: rgba(18,26,43,0.92);
      backdrop-filter: blur(10px);
      box-shadow: 0 16px 48px rgba(0,0,0,0.45);
      display: none;
      z-index: 9999;
    }
    .popover.open { display: block; }
    .popover-hd {
      padding: 12px 14px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
    }
    .popover-bd { padding: 12px 14px; }
    .popover-ft {
      padding: 12px 14px;
      border-top: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div>
        <h1>LogScope Web 控制台</h1>
        <div class="sub">同域调用 <span class="mono">/api/logscope/search</span>，返回下载链接（文件默认 120 秒清理）。</div>
      </div>
      <div class="tag">FastAPI</div>
    </div>

    <div class="grid">
      <div class="card">
        <div class="row">
          <div>
            <label>Authorization Token（Bearer）</label>
            <input id="token" placeholder="your-secret-admin-token" />
            <div class="hint">仅存本地浏览器 localStorage，不会发送到除本服务外的任何地方。</div>
          </div>
          <div>
            <label>Index</label>
            <input id="index" value=".ds-filebeat*" />
          </div>
        </div>

        <div class="row">
          <div>
            <label>ES Host</label>
            <input id="es_host" placeholder="https://your-es:9200" />
          </div>
          <div>
            <label>ES API Key</label>
            <input id="es_api_key" placeholder="base64..." />
          </div>
        </div>

        <div class="row3">
          <div>
            <label>Query（Lucene query_string）</label>
            <input id="query" value="*" />
          </div>
          <div>
            <label>Start Time（可选）</label>
            <input id="start_time" placeholder="点击选择…" readonly />
          </div>
          <div>
            <label>End Time（可选）</label>
            <input id="end_time" placeholder="点击选择…" readonly />
          </div>
        </div>

        <div class="row3">
          <div>
            <label>Size（最大导出条数）</label>
            <input id="size" type="number" min="1" max="200000" value="1000" />
          </div>
          <div>
            <label>Filters（match_phrase）</label>
            <div class="hint">下面表格每行一对 key/value，value 为空会忽略。</div>
          </div>
          <div class="actions" style="justify-content:flex-end; align-items:flex-end; padding-top: 24px;">
            <button class="secondary" id="pickTime">选择时间</button>
            <button class="secondary" id="clearTime">清空时间</button>
            <button class="secondary" id="addFilter">+ 添加过滤</button>
            <button class="secondary" id="save">保存到本地</button>
            <button id="run">查询并导出</button>
          </div>
        </div>

        <table class="filters" id="filtersTable">
          <thead><tr><th style="width:46%;">Key</th><th style="width:46%;">Value</th><th style="width:8%;">操作</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>

      <div class="card">
        <div class="actions" style="justify-content:space-between;">
          <div class="hint">结果</div>
          <div id="status" class="hint"></div>
        </div>
        <div style="height:10px;"></div>
        <div id="out"></div>
      </div>
    </div>
  </div>

  <div id="timePopover" class="popover" role="dialog" aria-modal="false" aria-label="时间范围选择">
    <div class="popover-hd">
      <div>
        <div style="font-weight: 650;">时间范围</div>
        <div class="hint">选择后写回表单（YYYY-MM-DDTHH:MM:SS）。</div>
      </div>
      <button class="secondary" id="timeClose" title="关闭">关闭</button>
    </div>
    <div class="popover-bd">
      <div class="row">
        <div>
          <label>Start</label>
          <div class="row" style="grid-template-columns: 1fr 1fr;">
            <div>
              <label style="margin-top:0;">日期</label>
              <div class="actions" style="gap:8px;">
                <input id="dlg_start_date" type="date" />
                <button class="secondary" id="pickStartDate" type="button">选日期</button>
              </div>
            </div>
            <div>
              <label style="margin-top:0;">时间</label>
              <input id="dlg_start_time" type="time" step="1" />
            </div>
          </div>
        </div>
        <div>
          <label>End</label>
          <div class="row" style="grid-template-columns: 1fr 1fr;">
            <div>
              <label style="margin-top:0;">日期</label>
              <div class="actions" style="gap:8px;">
                <input id="dlg_end_date" type="date" />
                <button class="secondary" id="pickEndDate" type="button">选日期</button>
              </div>
            </div>
            <div>
              <label style="margin-top:0;">时间</label>
              <input id="dlg_end_time" type="time" step="1" />
            </div>
          </div>
        </div>
      </div>
      <div style="height:10px;"></div>
      <div class="hint">快捷：</div>
      <div style="height:8px;"></div>
      <div class="mini-actions">
        <button class="secondary" data-preset="today">今天 00:00 → 现在</button>
        <button class="secondary" data-preset="5m">最近 5 分钟</button>
        <button class="secondary" data-preset="15m">最近 15 分钟</button>
        <button class="secondary" data-preset="1h">最近 1 小时</button>
      </div>
    </div>
    <div class="popover-ft">
      <div class="hint">不选时间：默认从当天 00:00:00（北京）开始。</div>
      <div class="actions">
        <button class="danger" id="timeClear">清空</button>
        <button id="timeApply">应用</button>
      </div>
    </div>
  </div>

  <script>
    const $ = (id) => document.getElementById(id);
    const LS_KEY = "logscope.console.v1";

    function nowISO() {
      const d = new Date();
      const pad = (n) => String(n).padStart(2, "0");
      return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    }

    function parseIsoToDateTimeParts(iso) {
      // 允许：YYYY-MM-DDTHH:MM:SS（无时区）或浏览器可解析格式（带时区）
      const s = (iso || "").trim();
      if (!s) return { date: "", time: "" };

      const m = s.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(?::(\d{2}))?$/);
      if (m) return { date: m[1], time: `${m[2]}:${m[3] || "00"}` };

      const dt = new Date(s);
      if (isNaN(dt.getTime())) return { date: "", time: "" };
      const pad = (n) => String(n).padStart(2, "0");
      return {
        date: `${dt.getFullYear()}-${pad(dt.getMonth()+1)}-${pad(dt.getDate())}`,
        time: `${pad(dt.getHours())}:${pad(dt.getMinutes())}:${pad(dt.getSeconds())}`
      };
    }

    function buildIsoFromParts(date, time) {
      const d = (date || "").trim();
      if (!d) return "";
      const t = (time || "").trim();
      if (!t) return `${d}T00:00:00`;
      // type=time 可能输出 HH:MM 或 HH:MM:SS
      const m = t.match(/^(\d{2}):(\d{2})(?::(\d{2}))?$/);
      if (!m) return `${d}T${t}`;
      return `${d}T${m[1]}:${m[2]}:${m[3] || "00"}`;
    }

    function openTimePopover() {
      const pop = $("timePopover");
      const s = parseIsoToDateTimeParts($("start_time").value);
      const e = parseIsoToDateTimeParts($("end_time").value);
      $("dlg_start_date").value = s.date;
      $("dlg_start_time").value = s.time;
      $("dlg_end_date").value = e.date;
      $("dlg_end_time").value = e.time;
      if (pop) pop.classList.add("open");

      // 尝试自动弹出日期选择器（部分浏览器支持 showPicker）
      setTimeout(() => {
        const el = $("dlg_start_date");
        if (!el) return;
        el.focus();
        try { if (el.showPicker) el.showPicker(); } catch (e) {}
      }, 0);
    }

    function closeTimePopover() {
      const pop = $("timePopover");
      if (pop) pop.classList.remove("open");
    }

    function applyTimePopover() {
      const s = buildIsoFromParts($("dlg_start_date").value, $("dlg_start_time").value);
      const e = buildIsoFromParts($("dlg_end_date").value, $("dlg_end_time").value);
      $("start_time").value = s;
      $("end_time").value = e;
      closeTimePopover();
    }

    function clearTime() {
      $("start_time").value = "";
      $("end_time").value = "";
      $("dlg_start_date").value = "";
      $("dlg_start_time").value = "";
      $("dlg_end_date").value = "";
      $("dlg_end_time").value = "";
    }

    function setPreset(kind) {
      const now = new Date();
      const pad = (n) => String(n).padStart(2, "0");
      const fmtDate = (d) => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
      const fmtTime = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;

      if (kind === "today") {
        const start = new Date(now);
        start.setHours(0,0,0,0);
        $("dlg_start_date").value = fmtDate(start);
        $("dlg_start_time").value = fmtTime(start);
        $("dlg_end_date").value = fmtDate(now);
        $("dlg_end_time").value = fmtTime(now);
        return;
      }

      const mins = kind === "5m" ? 5 : kind === "15m" ? 15 : kind === "1h" ? 60 : 0;
      if (mins > 0) {
        const start = new Date(now.getTime() - mins * 60 * 1000);
        $("dlg_start_date").value = fmtDate(start);
        $("dlg_start_time").value = fmtTime(start);
        $("dlg_end_date").value = fmtDate(now);
        $("dlg_end_time").value = fmtTime(now);
      }
    }

    function addFilterRow(k = "", v = "") {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><input class="fkey" placeholder="container.labels.service_project" value="${k.replaceAll('"','&quot;')}" /></td>
        <td><input class="fval" placeholder="umcare" value="${v.replaceAll('"','&quot;')}" /></td>
        <td><button class="danger" title="删除">删</button></td>
      `;
      tr.querySelector("button").addEventListener("click", () => tr.remove());
      $("filtersTable").querySelector("tbody").appendChild(tr);
    }

    function readFilters() {
      const rows = Array.from(document.querySelectorAll("#filtersTable tbody tr"));
      const obj = {};
      for (const r of rows) {
        const k = (r.querySelector(".fkey").value || "").trim();
        const v = (r.querySelector(".fval").value || "").trim();
        if (k && v) obj[k] = v;
      }
      return obj;
    }

    function loadLocal() {
      try {
        const raw = localStorage.getItem(LS_KEY);
        if (!raw) return;
        const s = JSON.parse(raw);
        if (s.token) $("token").value = s.token;
        if (s.index) $("index").value = s.index;
        if (s.es_host) $("es_host").value = s.es_host;
        if (s.es_api_key) $("es_api_key").value = s.es_api_key;
        if (s.query) $("query").value = s.query;
        if (s.size) $("size").value = s.size;
        if (s.start_time) $("start_time").value = s.start_time;
        if (s.end_time) $("end_time").value = s.end_time;
        $("filtersTable").querySelector("tbody").innerHTML = "";
        const fs = s.filters || {};
        const keys = Object.keys(fs);
        if (keys.length === 0) addFilterRow("container.labels.service_project", "");
        else keys.forEach(k => addFilterRow(k, fs[k]));
      } catch (e) {
        // ignore
      }
    }

    function saveLocal() {
      const state = {
        token: $("token").value.trim(),
        index: $("index").value.trim(),
        es_host: $("es_host").value.trim(),
        es_api_key: $("es_api_key").value.trim(),
        query: $("query").value.trim(),
        start_time: $("start_time").value.trim(),
        end_time: $("end_time").value.trim(),
        size: Number($("size").value || 1000),
        filters: readFilters()
      };
      localStorage.setItem(LS_KEY, JSON.stringify(state));
      setStatus("已保存到本地", "ok");
      setTimeout(() => setStatus("", ""), 1200);
    }

    function setStatus(msg, kind) {
      const el = $("status");
      el.className = `hint status ${kind || ""}`;
      el.textContent = msg || "";
    }

    function setOut(html) {
      $("out").innerHTML = html;
    }

    async function run() {
      setStatus("请求中…", "");
      setOut(`<pre class="mono">正在调用 /api/logscope/search …</pre>`);

      const token = $("token").value.trim();
      if (!token) {
        setStatus("缺少 token", "bad");
        setOut(`<pre class="mono">请先填写 Authorization Token。</pre>`);
        return;
      }

      const body = {
        index: $("index").value.trim(),
        es_host: $("es_host").value.trim() || undefined,
        es_api_key: $("es_api_key").value.trim() || undefined,
        query: $("query").value.trim() || "*",
        start_time: $("start_time").value.trim() || undefined,
        end_time: $("end_time").value.trim() || undefined,
        size: Number($("size").value || 1000),
        filters: readFilters()
      };

      // 清理 undefined（FastAPI/Pydantic 兼容）
      Object.keys(body).forEach(k => (body[k] === undefined || body[k] === "" || (k === "filters" && Object.keys(body.filters).length === 0)) && delete body[k]);

      try {
        const resp = await fetch("/api/logscope/search", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify(body)
        });

        const text = await resp.text();
        if (!resp.ok) {
          setStatus(`失败：HTTP ${resp.status}`, "bad");
          setOut(`<pre class="mono">${text}</pre>`);
          return;
        }

        const url = text.trim();
        setStatus("成功", "ok");
        const safe = url.replaceAll("<","&lt;").replaceAll(">","&gt;");
        const file = url.split("/").pop();
        const viewUrl = `/view/${encodeURIComponent(file)}`;
        setOut(`
          <div class="hint">下载链接：</div>
          <div style="height:8px;"></div>
          <pre class="mono">${safe}</pre>
          <div style="height:10px;"></div>
          <div class="actions">
            <button class="secondary" id="downloadBtn" type="button">下载（带 token）</button>
            <a href="${viewUrl}" target="_blank" rel="noreferrer">在线打开</a>
            <button class="secondary" id="copy">复制链接</button>
          </div>
        `);
        const dlBtn = document.getElementById("downloadBtn");
        if (dlBtn) {
          dlBtn.addEventListener("click", async () => {
            try {
              setStatus("下载中…", "");
              const resp2 = await fetch(`/api/logscope/download/${encodeURIComponent(file)}`, {
                headers: { "Authorization": `Bearer ${token}` }
              });
              const blob = await resp2.blob();
              if (!resp2.ok) {
                const t = await blob.text();
                setStatus(`下载失败：HTTP ${resp2.status}`, "bad");
                setOut(`<pre class="mono">${t}</pre>`);
                return;
              }
              const a = document.createElement("a");
              const u = URL.createObjectURL(blob);
              a.href = u;
              a.download = file || "log.txt";
              document.body.appendChild(a);
              a.click();
              a.remove();
              URL.revokeObjectURL(u);
              setStatus("成功", "ok");
            } catch (e) {
              setStatus("下载异常", "bad");
            }
          });
        }
        const copyBtn = document.getElementById("copy");
        if (copyBtn) {
          copyBtn.addEventListener("click", async () => {
            try {
              await navigator.clipboard.writeText(url);
              setStatus("已复制", "ok");
              setTimeout(() => setStatus("成功", "ok"), 900);
            } catch (e) {
              setStatus("复制失败（浏览器权限限制）", "bad");
            }
          });
        }
      } catch (e) {
        setStatus("请求异常", "bad");
        setOut(`<pre class="mono">${String(e)}</pre>`);
      }
    }

    $("pickTime").addEventListener("click", (e) => { e.preventDefault(); openTimePopover(); });
    $("start_time").addEventListener("click", (e) => { e.preventDefault(); openTimePopover(); });
    $("end_time").addEventListener("click", (e) => { e.preventDefault(); openTimePopover(); });
    $("clearTime").addEventListener("click", (e) => { e.preventDefault(); clearTime(); saveLocal(); });
    $("timeClose").addEventListener("click", (e) => { e.preventDefault(); closeTimePopover(); });
    $("timeApply").addEventListener("click", (e) => { e.preventDefault(); applyTimePopover(); saveLocal(); });
    $("timeClear").addEventListener("click", (e) => { e.preventDefault(); clearTime(); saveLocal(); closeTimePopover(); });

    // 兜底：显式按钮触发原生日历
    $("pickStartDate").addEventListener("click", (e) => {
      e.preventDefault();
      const el = $("dlg_start_date");
      el.focus();
      try { if (el.showPicker) el.showPicker(); } catch (err) {}
    });
    $("pickEndDate").addEventListener("click", (e) => {
      e.preventDefault();
      const el = $("dlg_end_date");
      el.focus();
      try { if (el.showPicker) el.showPicker(); } catch (err) {}
    });

    document.querySelectorAll("button[data-preset]").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        setPreset(btn.getAttribute("data-preset"));
      });
    });

    // 点击浮层外部关闭（保留 Kibana 那种“右下角弹出”的感觉）
    document.addEventListener("mousedown", (e) => {
      const pop = $("timePopover");
      if (!pop || !pop.classList.contains("open")) return;
      const target = e.target;
      if (pop.contains(target)) return;
      if (target === $("pickTime") || target === $("start_time") || target === $("end_time")) return;
      closeTimePopover();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeTimePopover();
    });

    $("addFilter").addEventListener("click", () => addFilterRow("", ""));
    $("save").addEventListener("click", saveLocal);
    $("run").addEventListener("click", async () => { saveLocal(); await run(); });

    // 初始加载
    loadLocal();
    // readonly 字段，提示用户使用弹窗选择
  </script>
</body>
</html>
"""
    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/view/{file}", response_class=HTMLResponse, include_in_schema=False)
async def view_file(file: str):
    """
    在线查看导出的日志文件：
    - 页面本身不要求 Header（便于新标签页打开）
    - 页面内用 localStorage 保存的 token，fetch 下载接口并展示内容
    """
    safe_file = (file or "").strip().replace('"', "").replace("'", "")
    html = rf"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LogScope 在线查看</title>
  <style>
    :root {{
      --bg: #0b1220;
      --panel: #121a2b;
      --muted: #93a4c7;
      --text: #e8eefc;
      --border: rgba(255,255,255,0.10);
      --accent: #4f8cff;
      --danger: #ff5a7a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
      background: var(--bg);
      color: var(--text);
    }}
    .wrap {{ max-width: 1100px; margin: 22px auto; padding: 0 16px; }}
    .top {{
      display:flex; justify-content: space-between; align-items: center; gap: 12px;
      margin-bottom: 12px;
    }}
    .card {{
      background: rgba(18,26,43,0.72);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      backdrop-filter: blur(10px);
    }}
    .hint {{ color: var(--muted); font-size: 12px; }}
    a {{ color: var(--accent); }}
    .actions {{ display:flex; gap:10px; align-items:center; flex-wrap: wrap; }}
    button {{
      border: 1px solid var(--border);
      background: rgba(10,16,28,0.35);
      color: var(--text);
      padding: 8px 10px;
      border-radius: 10px;
      cursor: pointer;
    }}
    button.danger {{ border-color: rgba(255,90,122,0.55); }}
    pre {{
      margin: 0; padding: 12px; border-radius: 12px; overflow: auto;
      border: 1px solid var(--border);
      background: rgba(10,16,28,0.55);
      color: #d7e3ff;
      font-size: 12px;
      line-height: 1.45;
      white-space: pre;
    }}
    /* 自动换行（更适合阅读长行日志） */
    pre.wrap {{
      white-space: pre-wrap;
      word-break: break-word;
      overflow-wrap: anywhere;
    }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div>
        <div style="font-weight:650;">在线查看</div>
        <div class="hint">文件：<span class="mono">{safe_file}</span></div>
      </div>
      <div class="actions">
        <a class="mono" href="/console" target="_blank" rel="noreferrer">返回控制台</a>
        <button id="downloadBtn" type="button">下载（带 token）</button>
        <button id="toggleWrap" type="button">自动换行：开</button>
        <button class="danger" id="clearToken">清空 token</button>
      </div>
    </div>

    <div class="card">
      <div class="hint">提示：该页面会从浏览器 localStorage 读取 token，并带 Authorization 去请求下载接口。</div>
      <div style="height:10px;"></div>
      <div id="status" class="hint"></div>
      <div style="height:10px;"></div>
      <pre id="content" class="mono wrap">加载中…</pre>
    </div>
  </div>

  <script>
    const LS_KEY = "{_LS_KEY}";
    const WRAP_KEY = "logscope.view.wrap.v1";
    const file = "{safe_file}";
    const statusEl = document.getElementById("status");
    const pre = document.getElementById("content");
    const previewUrl = `/api/logscope/preview/${{encodeURIComponent(file)}}`;
    const downloadUrl = `/api/logscope/download/${{encodeURIComponent(file)}}`;
    const wrapBtn = document.getElementById("toggleWrap");
    document.getElementById("downloadBtn").addEventListener("click", async () => {{
      const token = getToken();
      if (!token) {{
        setStatus("未找到 token：请先在 /console 填写并保存。", true);
        return;
      }}
      try {{
        setStatus("下载中…");
        const resp = await fetch(downloadUrl, {{
          headers: {{ "Authorization": `Bearer ${{token}}` }}
        }});
        const blob = await resp.blob();
        if (!resp.ok) {{
          const t = await blob.text();
          setStatus(`下载失败：HTTP ${{resp.status}}`, true);
          pre.textContent = t;
          return;
        }}
        const a = document.createElement("a");
        const u = URL.createObjectURL(blob);
        a.href = u;
        a.download = file || "log.txt";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(u);
        setStatus("下载成功");
      }} catch (e) {{
        setStatus("下载异常", true);
      }}
    }});

    function getToken() {{
      try {{
        const raw = localStorage.getItem(LS_KEY);
        if (!raw) return "";
        const s = JSON.parse(raw);
        return (s.token || "").trim();
      }} catch (e) {{
        return "";
      }}
    }}

    function setStatus(msg, bad=false) {{
      statusEl.textContent = msg || "";
      statusEl.style.color = bad ? "var(--danger)" : "var(--muted)";
    }}

    function getWrapEnabled() {{
      try {{
        const v = localStorage.getItem(WRAP_KEY);
        if (v === null) return true; // 默认开启
        return v === "1";
      }} catch (e) {{
        return true;
      }}
    }}

    function setWrapEnabled(enabled) {{
      try {{ localStorage.setItem(WRAP_KEY, enabled ? "1" : "0"); }} catch (e) {{}}
      if (enabled) pre.classList.add("wrap");
      else pre.classList.remove("wrap");
      wrapBtn.textContent = enabled ? "自动换行：开" : "自动换行：关";
    }}

    async function load() {{
      const token = getToken();
      if (!token) {{
        setStatus("未找到 token：请先在 /console 填写并保存。", true);
        pre.textContent = "无法加载：缺少 Authorization Token。";
        return;
      }}
      setStatus("请求中…");
      try {{
        const resp = await fetch(previewUrl, {{
          headers: {{ "Authorization": `Bearer ${{token}}` }}
        }});
        const text = await resp.text();
        if (!resp.ok) {{
          setStatus(`失败：HTTP ${{resp.status}}`, true);
          pre.textContent = text;
          return;
        }}
        setStatus("预览加载成功（仅前 200KB）");
        pre.textContent = text || "(空文件)";
      }} catch (e) {{
        setStatus("请求异常", true);
        pre.textContent = String(e);
      }}
    }}

    document.getElementById("clearToken").addEventListener("click", () => {{
      try {{
        const raw = localStorage.getItem(LS_KEY);
        if (raw) {{
          const s = JSON.parse(raw);
          s.token = "";
          localStorage.setItem(LS_KEY, JSON.stringify(s));
        }}
      }} catch (e) {{}}
      load();
    }});

    wrapBtn.addEventListener("click", () => {{
      setWrapEnabled(!pre.classList.contains("wrap"));
    }});

    // 初始化换行偏好（默认开）
    setWrapEnabled(getWrapEnabled());

    load();
  </script>
</body>
</html>
"""
    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "no-store"},
    )


