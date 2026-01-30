# coding=utf-8
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.search import router as search_router
from app.api.admin import router as admin_router
from app.web.console import router as console_router
from app.web.admin import router as admin_page_router
from app.core.es import init_es, close_es
from app.storage.config_db import init_db

app = FastAPI(title="LogScope API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()
    await init_es(app)

@app.on_event("shutdown")
async def shutdown():
    await close_es(app)

app.include_router(search_router, prefix="/api/logscope")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(console_router)
app.include_router(admin_page_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
