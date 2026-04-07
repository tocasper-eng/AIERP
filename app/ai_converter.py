import anthropic
from app.config import settings
from app.schema_cache import get_schema_for_prompt

_client: anthropic.Anthropic | None = None

_SYSTEM_PROMPT = """\
你是一個 SQL Server (T-SQL) 資料庫查詢專家，負責將用戶的自然語言問題轉換為可執行的 T-SQL SELECT 查詢。

【規則】
1. 只輸出純 SQL，不加任何說明文字、不用 ```sql``` 包裹
2. 只允許 SELECT（唯讀），禁止 INSERT / UPDATE / DELETE / DROP / ALTER
3. 使用 TOP N 限制筆數（預設 TOP 100），除非用戶明確要求全部
4. 使用繁體中文別名（AS）讓結果更易讀，例如 accino AS 會計科目
5. 日期格式：YYYY-MM-DD
6. 若有計算欄位請加別名
7. 遇到不確定的情況，選擇最合理的解釋

【資料庫】
資料庫名稱：{db}（SQL Server）

【資料表結構】
{schema}
"""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


async def convert_to_sql(question: str) -> str:
    """將自然語言問題轉換為 T-SQL。"""
    schema = get_schema_for_prompt(question)
    system = _SYSTEM_PROMPT.format(db=settings.DB_DATABASE, schema=schema)

    client = _get_client()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": question}],
    )

    sql = message.content[0].text.strip()

    # 清除可能夾帶的 markdown code block
    if sql.startswith("```"):
        lines = sql.splitlines()
        sql = "\n".join(lines[1:-1]).strip()

    return sql
