import json
import os
from app.database import get_connection

CACHE_FILE = "schema_cache.json"
ALIAS_FILE = "table_aliases.json"  # 可選，僅用於補充額外關鍵字

_schema: dict[str, list[dict]] = {}
_aliases: dict = {}


def _load_aliases() -> dict:
    if os.path.exists(ALIAS_FILE):
        with open(ALIAS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_from_db() -> dict[str, list[dict]]:
    """從資料庫讀取所有資料表與 View 的欄位定義。"""
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
                AND t.TABLE_TYPE IN ('BASE TABLE', 'VIEW')
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
        print(f"[Schema] 從快取載入 {len(_schema)} 個資料表/View")
        return
    _schema = _load_from_db()
    _save_cache()
    print(f"[Schema] 從資料庫建立快取，共 {len(_schema)} 個資料表/View")


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
    """根據問題找出相關資料表/View，回傳 schema 文字供 prompt 注入。"""
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
        lines.append(f"資料表/View：{table}\n" + "\n".join(col_parts))
    return "\n\n".join(lines)


def _name_substrings(name: str, min_len: int = 2, max_len: int = 6) -> list[str]:
    """萃取名稱中所有長度在 min_len~max_len 之間的子字串（用於中文命名比對）。"""
    result = []
    for length in range(min_len, min(len(name) + 1, max_len + 1)):
        for i in range(len(name) - length + 1):
            result.append(name[i:i + length])
    return result


def _find_relevant_tables(question: str) -> list[str]:
    scored: list[tuple[int, str]] = []

    for table, cols in _schema.items():
        score = 0

        # 完整名稱命中（最高分）
        if table in question:
            score += 20

        # 名稱子字串命中（適用中文 View 名如「科目餘額表」）
        for substr in _name_substrings(table):
            if substr in question:
                score += len(substr)  # 越長的子串得分越高

        # 欄位名稱命中（中文欄位直接比對）
        for c in cols:
            col_name = c["column"]
            if col_name in question:
                score += 5
            else:
                # 欄位名稱子字串
                for substr in _name_substrings(col_name):
                    if substr in question:
                        score += len(substr) - 1

        # 可選：table_aliases.json 補充關鍵字
        for kw in _aliases.get(table, {}).get("keywords", []):
            if kw in question:
                score += 8

        if score > 0:
            scored.append((score, table))

    if scored:
        scored.sort(reverse=True)
        return [t for _, t in scored[:15]]

    # 無命中時回傳全部（最多 30 個）
    return sorted(_schema.keys())[:30]
