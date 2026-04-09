import json
import os
from app.database import get_connection

CACHE_FILE = "schema_cache.json"
ALIAS_FILE = "table_aliases.json"

_schema: dict[str, list[dict]] = {}
_aliases: dict = {}


def _load_aliases() -> dict:
    if os.path.exists(ALIAS_FILE):
        with open(ALIAS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_from_db() -> dict[str, list[dict]]:
    """從資料庫讀取所有資料表的欄位定義。"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                c.TABLE_NAME,
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.CHARACTER_MAXIMUM_LENGTH,
                c.IS_NULLABLE,
                CAST(ep.value AS NVARCHAR(500)) AS COLUMN_DESCRIPTION
            FROM INFORMATION_SCHEMA.COLUMNS c
            JOIN INFORMATION_SCHEMA.TABLES t
                ON c.TABLE_NAME = t.TABLE_NAME
                AND t.TABLE_TYPE = 'BASE TABLE'
            LEFT JOIN sys.extended_properties ep
                ON ep.major_id = OBJECT_ID(c.TABLE_NAME)
                AND ep.minor_id = c.ORDINAL_POSITION
                AND ep.name = 'MS_Description'
                AND ep.class = 1
            ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
        """)
        result: dict[str, list[dict]] = {}
        for row in cursor.fetchall():
            table, col, dtype, maxlen, nullable, desc = row
            if table not in result:
                result[table] = []
            col_info: dict = {"column": col, "type": dtype}
            if maxlen:
                col_info["max_length"] = maxlen
            if nullable == "YES":
                col_info["nullable"] = True
            if desc:
                col_info["description"] = desc
            result[table].append(col_info)
        return result
    finally:
        conn.close()


async def init_schema_cache() -> None:
    """啟動時初始化 schema 快取（有快取檔案則直接載入）。"""
    global _schema, _aliases
    _aliases = _load_aliases()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            _schema = json.load(f)
        print(f"[Schema] 從快取載入 {len(_schema)} 個資料表")
        return
    _schema = _load_from_db()
    _save_cache()
    print(f"[Schema] 從資料庫建立快取，共 {len(_schema)} 個資料表")


def refresh_schema_cache() -> int:
    """強制重新從資料庫讀取並更新快取。"""
    global _schema, _aliases
    _aliases = _load_aliases()
    _schema = _load_from_db()
    _save_cache()
    return len(_schema)


def _save_cache() -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(_schema, f, ensure_ascii=False, indent=2)


def get_all_table_names() -> list[str]:
    return sorted(_schema.keys())


def get_schema_for_prompt(question: str) -> str:
    """根據問題關鍵字找出相關資料表，回傳 schema 文字供 prompt 注入。"""
    if not _schema:
        return "（Schema 尚未載入）"

    relevant = _find_relevant_tables(question)
    lines: list[str] = []
    for table in relevant:
        cols = _schema.get(table, [])
        col_parts = []
        for c in cols:
            desc = f"  --{c['description']}" if c.get("description") else ""
            col_parts.append(f"    {c['column']} ({c['type']}){desc}")
        table_desc = _aliases.get(table, {}).get("description", "")
        header = f"資料表 {table}（{table_desc}）:" if table_desc else f"資料表 {table}:"
        lines.append(header + "\n" + "\n".join(col_parts))
    return "\n\n".join(lines)


def _find_relevant_tables(question: str) -> list[str]:
    scored: list[tuple[int, str]] = []

    for table, cols in _schema.items():
        score = 0

        # 英文資料表名稱命中
        if table.lower() in question.lower():
            score += 15

        # alias 中文描述命中
        alias_info = _aliases.get(table, {})
        table_desc = alias_info.get("description", "")
        if table_desc and table_desc in question:
            score += 10

        # alias 關鍵字命中
        for kw in alias_info.get("keywords", []):
            if kw in question:
                score += 8

        # 欄位名稱命中
        for c in cols:
            if c["column"].lower() in question.lower():
                score += 3
            desc = c.get("description", "")
            if desc and any(kw in question for kw in desc.split()):
                score += 2

        if score > 0:
            scored.append((score, table))

    if scored:
        scored.sort(reverse=True)
        return [t for _, t in scored[:15]]

    # 無關鍵字命中時回傳全部（最多 30 個）
    return sorted(_schema.keys())[:30]
