import pyodbc
from app.config import settings

# 依序嘗試可用的 ODBC 驅動程式
_DRIVER_FALLBACKS = [
    settings.DB_DRIVER,
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "SQL Server",
]

_SAFE_KEYWORDS = {"select", "with"}
_DANGEROUS_KEYWORDS = {"drop", "delete", "truncate", "insert", "update", "alter", "exec", "execute", "create"}


def _build_conn_str(driver: str) -> str:
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={settings.DB_SERVER};"
        f"DATABASE={settings.DB_DATABASE};"
        f"UID={settings.DB_USERNAME};"
        f"PWD={settings.DB_PASSWORD};"
        "TrustServerCertificate=yes;"
        "Encrypt=no;"
    )


def get_connection() -> pyodbc.Connection:
    last_err = None
    for driver in _DRIVER_FALLBACKS:
        try:
            return pyodbc.connect(_build_conn_str(driver), timeout=10)
        except pyodbc.Error as e:
            last_err = e
    raise ConnectionError(f"無法連線資料庫，請確認 ODBC 驅動程式已安裝。最後錯誤：{last_err}")


def validate_sql(sql: str) -> None:
    """拒絕非 SELECT 的危險語句。"""
    first_word = sql.strip().lower().split()[0] if sql.strip() else ""
    if first_word not in _SAFE_KEYWORDS:
        raise ValueError(f"安全限制：不允許執行 '{first_word.upper()}' 語句，僅允許 SELECT 查詢。")
    for kw in _DANGEROUS_KEYWORDS:
        if f" {kw} " in f" {sql.lower()} ":
            raise ValueError(f"安全限制：SQL 包含禁止關鍵字 '{kw.upper()}'。")


def execute_query(sql: str) -> tuple[list[str], list[list]]:
    """執行 SELECT 查詢，回傳 (欄位名稱, 資料列)。"""
    validate_sql(sql)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = []
        for row in cursor.fetchall():
            rows.append([str(v) if v is not None else None for v in row])
        return columns, rows
    finally:
        conn.close()
