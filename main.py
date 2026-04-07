from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes import router
from app.schema_cache import init_schema_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[AIERP] 啟動中，載入資料庫 Schema...")
    try:
        await init_schema_cache()
        print("[AIERP] Schema 載入完成，服務就緒。")
    except Exception as e:
        print(f"[AIERP] 警告：Schema 載入失敗（{e}），查詢功能可能受限。")
    yield
    print("[AIERP] 服務關閉。")


app = FastAPI(
    title="AIERP 自然語言查詢系統",
    description="以自然語言查詢 ERP 資料庫",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
