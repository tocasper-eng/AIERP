
請規劃這套 **自然語言轉 SQL 的 Python 入口網站**。

---

## 架構設計

```
用戶輸入自然語言
       ↓
  Python Web App (FastAPI)
       ↓
  Claude AI (NL → SQL 轉換)
  + 資料庫 Schema 注入 (RAG)
       ↓
  SQL Server 執行
       ↓
  結果呈現 (表格/圖表)
```


## 技術選型建議

| 元件        | 建議                                 | 理由                 |
| --------- | ---------------------------------- | ------------------ |
| Web 框架    | **FastAPI**                        | 輕量、async、自動 API 文件 |
| AI 轉換     | **Claude API** (claude-sonnet-4-6) | 您已熟悉               |
| DB 驅動     | **pyodbc / SQLAlchemy**            | SQL Server 支援佳     |
| 前端        | **HTMX + Bootstrap**               | 輕量、不需前後端分離         |
| Schema 快取 | **JSON/SQLite**                    | 儲存資料表結構供 prompt 使用 |

## 核心流程說明

**1. Schema 注入 (關鍵)**

- 啟動時從 SQL Server 讀取所有資料表欄位定義
- 用戶查詢時，將相關資料表 schema 注入到 Claude prompt
- 讓 Claude 產生精確的 SQL

### sql 連線資料如下：

database server:163.17.141.61,8000

database:Casper

id:drcas

pwd:CasChrAliJimJam

### 工作目錄 

C:\Users\tocas\Dropbox\claude\claude\nutc202603\AIERP
 
### 案例一 

table schema 

select 
accino  ,--會計科目
accinm ,--科目名稱
amt       ,--科目餘額
from acci  會計科目表

### 案例二 

table schema 

select 
pono ,--採購編號 
poseq,--項次
podate,--採購日期
podatew,--預定交期
itemno,--產品編號
itemnm,--產品名稱
ISNULL(poqty,0)-ISNULL(poqty_pu,0)-ISNULL(poqty_pox,0) as  已未交量
from pod 



 ### 發佈環境

 請上傳 github 
id:tocasper@g.ncu.edu.tw  
pwd:Casper@6153
repository: [AIERP](https://github.com/tocasper-eng/AIERP)

我要發佈到 zeabur  的 python 套件，請教我怎麼做？

 