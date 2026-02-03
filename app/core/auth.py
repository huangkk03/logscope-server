# coding=utf-8
import os
from fastapi import Request, HTTPException

# 通过环境变量配置（更适合 Linux 部署）：LOGSCOPE_AUTH_TOKEN
# 未设置时使用默认值（请在生产环境务必修改）。
AUTH_TOKEN = os.getenv("LOGSCOPE_AUTH_TOKEN", "your-secret-admin-token")

def check_auth(req: Request):
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(403, "Invalid Authorization header")

    token = auth.split(" ", 1)[1].strip()
    if token != AUTH_TOKEN:
        raise HTTPException(403, "Invalid Token")
