# coding=utf-8
from fastapi import Request, HTTPException

AUTH_TOKEN = "your-secret-admin-token"

def check_auth(req: Request):
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(403, "Invalid Authorization header")

    token = auth.split(" ", 1)[1].strip()
    if token != AUTH_TOKEN:
        raise HTTPException(403, "Invalid Token")
