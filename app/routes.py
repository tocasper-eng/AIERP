from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.ai_converter import convert_to_sql
from app.database import execute_query
from app.schema_cache import get_all_table_names, refresh_schema_cache

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    tables = get_all_table_names()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "tables": tables, "table_count": len(tables)},
    )


@router.post("/query", response_class=HTMLResponse)
async def query(request: Request, question: str = Form(...)):
    sql = ""
    columns: list[str] = []
    rows: list[list] = []
    error: str | None = None

    try:
        sql = await convert_to_sql(question)
        columns, rows = execute_query(sql)
    except Exception as e:
        error = str(e)

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "question": question,
            "sql": sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "error": error,
        },
    )


@router.post("/refresh-schema", response_class=JSONResponse)
async def refresh_schema():
    try:
        count = refresh_schema_cache()
        return {"success": True, "message": f"Schema 已更新，共 {count} 個資料表"}
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)
