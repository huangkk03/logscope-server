# coding=utf-8
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_page():
    # 仅前端页面；所有写操作都走 /api/admin/*，并由 Authorization 保护
    html = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LogScope 后台管理</title>
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
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
      background: radial-gradient(1200px 600px at 20% -10%, rgba(79,140,255,0.22), transparent 55%),
                  radial-gradient(900px 500px at 110% 10%, rgba(61,220,151,0.16), transparent 50%),
                  var(--bg);
      color: var(--text);
    }
    .wrap { max-width: 1100px; margin: 28px auto; padding: 0 18px; }
    .top { display:flex; justify-content: space-between; align-items:flex-end; gap: 12px; margin-bottom: 14px; }
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
    .row { display:grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    label { display:block; font-size: 12px; color: var(--muted); margin: 6px 0; }
    input, textarea, select {
      width: 100%;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: rgba(10,16,28,0.55);
      color: var(--text);
      padding: 10px 10px;
      outline: none;
    }
    textarea { min-height: 88px; resize: vertical; }
    .actions { display:flex; gap: 10px; align-items:center; flex-wrap: wrap; }
    button {
      border: 1px solid rgba(79,140,255,0.55);
      background: linear-gradient(180deg, rgba(79,140,255,0.35), rgba(79,140,255,0.16));
      color: var(--text);
      padding: 10px 12px;
      border-radius: 10px;
      cursor: pointer;
    }
    button.secondary { border-color: var(--border); background: rgba(10,16,28,0.35); color: var(--muted); }
    button.danger { border-color: rgba(255,90,122,0.55); background: linear-gradient(180deg, rgba(255,90,122,0.28), rgba(255,90,122,0.12)); }
    .hint { color: var(--muted); font-size: 12px; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    .list { width: 100%; border-collapse: collapse; margin-top: 8px; }
    .list th, .list td { border-bottom: 1px solid var(--border); padding: 8px 6px; font-size: 12px; }
    .list th { text-align:left; color: var(--muted); font-weight: 650; }
    pre { margin:0; padding:12px; border-radius: 12px; border:1px solid var(--border); background: rgba(10,16,28,0.55); overflow:auto; font-size:12px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div>
        <h1>LogScope 后台管理</h1>
        <div class="sub">配置 ES 连接与常用过滤条件（filters preset）。所有 API 需 Bearer Token。</div>
      </div>
      <div class="actions">
        <a class="mono" href="/console" target="_blank" rel="noreferrer">打开控制台</a>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <div class="row">
          <div>
            <label>Authorization Token（Bearer）</label>
            <input id="token" placeholder="your-secret-admin-token" />
            <div class="hint">保存到浏览器 localStorage：<span class="mono">logscope.admin.v1</span></div>
          </div>
          <div class="actions" style="justify-content:flex-end; align-items:flex-end; padding-top: 24px;">
            <button class="secondary" id="saveToken">保存 token</button>
            <button id="refresh">刷新列表</button>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="actions" style="justify-content:space-between;">
          <div style="font-weight:650;">ES 连接配置</div>
          <button class="secondary" id="newEs">新增</button>
        </div>
        <div class="hint">建议 name 用环境名/集群名（例如 sit-zejin）。API Key 不会出现在控制台页面里。</div>
        <table class="list" id="esList">
          <thead><tr><th style="width:10%;">ID</th><th style="width:20%;">Name</th><th style="width:50%;">Host</th><th style="width:20%;">操作</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>

      <div class="card">
        <div class="actions" style="justify-content:space-between;">
          <div style="font-weight:650;">Filters 预设</div>
          <button class="secondary" id="newPreset">新增</button>
        </div>
      <div class="hint">每条记录对应前台一行 filters：Key + 多个可选 Value（前台下拉多选）。</div>
        <table class="list" id="presetList">
          <thead><tr><th style="width:10%;">ID</th><th style="width:30%;">中文名</th><th style="width:40%;">Key</th><th style="width:20%;">操作</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>

      <div class="card">
        <div class="actions" style="justify-content:space-between;">
          <div style="font-weight:650;">输出</div>
          <button class="secondary" id="clearOut">清空</button>
        </div>
        <div style="height:8px;"></div>
        <pre id="out" class="mono">(空)</pre>
      </div>
    </div>
  </div>

  <script>
    const $ = (id) => document.getElementById(id);
    const LS = "logscope.admin.v1";
    const LS_CONSOLE = "logscope.console.v1";

    function out(msg) {
      $("out").textContent = msg || "(空)";
    }

    function getToken() {
      try {
        const t1 = (JSON.parse(localStorage.getItem(LS) || "{}").token || "").trim();
        if (t1) return t1;
        // 复用控制台保存的 token（避免后台页再粘贴一次）
        return (JSON.parse(localStorage.getItem(LS_CONSOLE) || "{}").token || "").trim();
      } catch (e) { return ""; }
    }

    function saveToken() {
      const token = $("token").value.trim();
      localStorage.setItem(LS, JSON.stringify({ token }));
      // 同步到控制台存储（可选，但更省事）
      try { localStorage.setItem(LS_CONSOLE, JSON.stringify({ token })); } catch (e) {}
      out("token 已保存");
    }

    async function api(path, opts={}) {
      const token = getToken();
      if (!token) throw new Error("缺少 token（请先保存）");
      const resp = await fetch(path, {
        ...opts,
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
          ...(opts.headers || {})
        }
      });
      const text = await resp.text();
      if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${text}`);
      return text ? JSON.parse(text) : {};
    }

    async function refresh() {
      try {
        const es = await api("/api/admin/es-configs");
        const tbody = $("esList").querySelector("tbody");
        tbody.innerHTML = "";
        es.forEach(x => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td class="mono">${x.id}</td>
            <td>${x.name}</td>
            <td class="mono">${x.host}</td>
            <td class="actions">
              <button class="secondary" data-act="edit-es" data-id="${x.id}">编辑</button>
              <button class="danger" data-act="del-es" data-id="${x.id}">删除</button>
            </td>
          `;
          tbody.appendChild(tr);
        });

        const ps = await api("/api/admin/filter-presets");
        const pt = $("presetList").querySelector("tbody");
        pt.innerHTML = "";
        ps.forEach(x => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td class="mono">${x.id}</td>
            <td>${(x.label && String(x.label).trim()) ? String(x.label) : "(未设置)"}</td>
            <td class="mono">${x.key ?? ""}</td>
            <td class="actions">
              <button class="secondary" data-act="edit-p" data-id="${x.id}">编辑</button>
              <button class="danger" data-act="del-p" data-id="${x.id}">删除</button>
            </td>
          `;
          pt.appendChild(tr);
        });

        out("刷新完成");
      } catch (e) {
        out(String(e));
      }
    }

    async function editEs(id) {
      try {
        const cur = id ? await api(`/api/admin/es-configs/${id}`) : { id: null, name: "", host: "", api_key: "" };
        const name = prompt("name（唯一）", cur.name || "");
        if (name === null) return;
        const host = prompt("host", cur.host || "");
        if (host === null) return;
        const apiKey = prompt("api_key（会保存到服务端）", cur.api_key || "");
        if (apiKey === null) return;
        const res = await api("/api/admin/es-configs", { method: "POST", body: JSON.stringify({ id: cur.id, name, host, api_key: apiKey }) });
        out(JSON.stringify(res, null, 2));
        await refresh();
      } catch (e) {
        out(String(e));
      }
    }

    async function delEs(id) {
      if (!confirm(`确认删除 ES 配置 #${id} ?`)) return;
      try {
        const res = await api(`/api/admin/es-configs/${id}`, { method: "DELETE" });
        out(JSON.stringify(res, null, 2));
        await refresh();
      } catch (e) {
        out(String(e));
      }
    }

    // Jenkins 风格：用一个小窗编辑多值（chips），并支持粘贴多行/逗号分隔
    function editValuesDialog(curKey, curValues) {
      return new Promise((resolve) => {
        const values = new Set((curValues || []).map(x => String(x).trim()).filter(Boolean));

        const overlay = document.createElement("div");
        overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.55);backdrop-filter:blur(6px);z-index:9999;display:flex;align-items:flex-end;justify-content:flex-end;padding:18px;";

        const panel = document.createElement("div");
        panel.style.cssText = "width:min(560px,calc(100vw - 24px));border:1px solid rgba(255,255,255,0.10);border-radius:14px;background:rgba(18,26,43,0.96);box-shadow:0 16px 48px rgba(0,0,0,0.45);overflow:hidden;";

        panel.innerHTML = `
          <div style="padding:12px 14px;border-bottom:1px solid rgba(255,255,255,0.10);display:flex;justify-content:space-between;gap:10px;align-items:center;">
            <div>
              <div style="font-weight:650;">编辑可选值</div>
              <div class="hint">Key：<span class="mono">${curKey}</span></div>
            </div>
            <button class="secondary" type="button" data-act="close">关闭</button>
          </div>
          <div style="padding:12px 14px;">
            <div class="hint">当前值（点击 x 删除）：</div>
            <div data-act="chips" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;"></div>
            <div style="height:10px;"></div>
            <div class="row" style="grid-template-columns: 1fr auto;">
              <div>
                <label style="margin-top:0;">新增</label>
                <input data-act="new" placeholder="输入一个值，回车添加" />
              </div>
              <div class="actions" style="justify-content:flex-end;align-items:flex-end;padding-top:24px;">
                <button class="secondary" type="button" data-act="add">添加</button>
              </div>
            </div>
            <div style="height:10px;"></div>
            <label>批量粘贴（多行或逗号分隔）</label>
            <textarea data-act="bulk" placeholder="umcare, other&#10;backend&#10;frontend"></textarea>
            <div style="height:10px;"></div>
            <div class="actions" style="justify-content:space-between;">
              <button class="danger" type="button" data-act="clear">清空</button>
              <button type="button" data-act="ok">保存</button>
            </div>
          </div>
        `;

        const chips = panel.querySelector('[data-act="chips"]');
        const newInput = panel.querySelector('[data-act="new"]');
        const bulk = panel.querySelector('[data-act="bulk"]');

        const render = () => {
          chips.innerHTML = "";
          Array.from(values).sort().forEach(v => {
            const chip = document.createElement("div");
            chip.style.cssText = "display:flex;gap:6px;align-items:center;border:1px solid rgba(255,255,255,0.10);background:rgba(10,16,28,0.45);padding:6px 8px;border-radius:999px;font-size:12px;";
            chip.innerHTML = `<span class="mono">${v}</span><button class="danger" type="button" style="padding:2px 6px;border-radius:999px;" title="删除">x</button>`;
            chip.querySelector("button").addEventListener("click", () => { values.delete(v); render(); });
            chips.appendChild(chip);
          });
        };

        const addOne = (v) => {
          const s = (v || "").trim();
          if (!s) return;
          values.add(s);
          render();
        };
        const addBulk = (t) => {
          const parts = (t || "").split(/[\r\n,]+/).map(x => x.trim()).filter(Boolean);
          parts.forEach(addOne);
        };

        panel.querySelector('[data-act="close"]').addEventListener("click", () => { overlay.remove(); resolve(null); });
        overlay.addEventListener("mousedown", (e) => { if (e.target === overlay) { overlay.remove(); resolve(null); }});
        panel.querySelector('[data-act="add"]').addEventListener("click", () => { addOne(newInput.value); newInput.value=""; newInput.focus(); });
        newInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); addOne(newInput.value); newInput.value=""; }});
        panel.querySelector('[data-act="clear"]').addEventListener("click", () => { values.clear(); render(); });
        panel.querySelector('[data-act="ok"]').addEventListener("click", () => { addBulk(bulk.value); overlay.remove(); resolve(Array.from(values)); });

        document.body.appendChild(overlay);
        overlay.appendChild(panel);
        render();
        setTimeout(() => newInput.focus(), 0);
      });
    }

    async function editPreset(id) {
      try {
        const cur = id ? await api(`/api/admin/filter-presets/${id}`) : { id: null, key: "container.labels.service_project", label: "服务项目", values: [] };
        const key = prompt("Key（对应前台 filters 的 key）", cur.key || "container.labels.service_project");
        if (key === null) return;
        const label = prompt("中文名（展示用）", cur.label || "");
        if (label === null) return;
        const values = await editValuesDialog(key, cur.values || []);
        if (values === null) return;
        const res = await api("/api/admin/filter-presets", { method: "POST", body: JSON.stringify({ id: cur.id, key, label, values }) });
        out(JSON.stringify(res, null, 2));
        await refresh();
      } catch (e) {
        out(String(e));
      }
    }

    async function delPreset(id) {
      if (!confirm(`确认删除 preset #${id} ?`)) return;
      try {
        const res = await api(`/api/admin/filter-presets/${id}`, { method: "DELETE" });
        out(JSON.stringify(res, null, 2));
        await refresh();
      } catch (e) {
        out(String(e));
      }
    }

    document.addEventListener("click", (e) => {
      const t = e.target;
      if (!t || !t.getAttribute) return;
      const act = t.getAttribute("data-act");
      const id = Number(t.getAttribute("data-id"));
      if (act === "edit-es") editEs(id);
      if (act === "del-es") delEs(id);
      if (act === "edit-p") editPreset(id);
      if (act === "del-p") delPreset(id);
    });

    $("saveToken").addEventListener("click", saveToken);
    $("refresh").addEventListener("click", refresh);
    $("newEs").addEventListener("click", () => editEs(null));
    $("newPreset").addEventListener("click", () => editPreset(null));
    $("clearOut").addEventListener("click", () => out("(空)"));

    // init
    $("token").value = getToken();
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


