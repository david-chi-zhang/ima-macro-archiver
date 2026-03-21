---
name: ima-macro-archiver
description: Extract macroeconomic data from TradingEconomics and archive to IMA notes with automatic date detection. Reuses macro-archiver workflow but outputs to IMA instead of markdown/Feishu.
---

# IMA Macro Economic Data Archiver

## Purpose

Automate extraction and archiving of macroeconomic data summaries from TradingEconomics into **IMA notes** with **automatic date detection** from the extracted text.

**复用 macro-archiver 的前面步骤**：
- ✅ 缓存策略（节约 token）
- ✅ 数据抓取（web_fetch）
- ✅ 日期识别（从文本中自动识别 YYYY-MM）
- ✅ 指标分类（GDP、PMI、Inflation 等）

**唯一区别**：最后写入 IMA 笔记，而不是 markdown 文件或飞书文档。

## Trigger Phrases

- "更新 [Country] [Indicator] 到 IMA"
- "extract economic data to IMA"
- "归档宏观经济数据到 IMA"

## Prerequisites

**IMA 凭证配置**（必须先完成）：

1. 打开 https://ima.qq.com/agent-interface 获取 **Client ID** 和 **Api Key**
2. 配置环境变量：
```bash
export IMA_OPENAPI_CLIENTID="your_client_id"
export IMA_OPENAPI_APIKEY="your_api_key"
```

3. 验证凭证：
```bash
ima_api "list_note_folder_by_cursor" '{"cursor": "0", "limit": 1}'
```

---

## Workflow

### Step 0: Validate IMA Credentials

**在开始任何操作之前，先验证 IMA 凭证是否可用**：

```bash
if [ -z "$IMA_OPENAPI_CLIENTID" ] || [ -z "$IMA_OPENAPI_APIKEY" ]; then
  echo "❌ 缺少 IMA 凭证，请先配置环境变量 IMA_OPENAPI_CLIENTID 和 IMA_OPENAPI_APIKEY"
  echo "获取地址：https://ima.qq.com/agent-interface"
  exit 1
fi

# 测试 API 连通性
test_result=$(ima_api "list_note_folder_by_cursor" '{"cursor": "0", "limit": 1}')
if ! echo "$test_result" | jq -e '.code == 0' > /dev/null; then
  echo "❌ IMA API 连通性测试失败，请检查凭证配置"
  exit 1
fi
```

---

### Step 1: Parse Request

- **Country**: US, EuroArea, Japan, SouthAfrica, Bangladesh, Global, China
- **Indicator**: GDP, PMI, Inflation, etc.
- **Year**: Current year (e.g., 2026)

**⚠️ 重要规则：选取指标严格遵循 url_library.json**

- 每个国家要更新什么指标，必须严格参照 `references/url-library-template.json` 中定义的结构
- 禁止自行添加或推断指标，只更新 JSON 文件中明确列出的指标
- 如果用户请求的指标不在 url_library.json 中，应提示用户该指标未配置

---

### Step 2: Check Cache & Validate (Token 优化)

**缓存策略**（复用 macro-archiver，节约 50-70% token）：

1. **检查缓存**：读取 `temp/macro_cache/{Country}_{Indicator}.json`
   - 如果缓存存在且 <24 小时 → 使用缓存数据
   - 如果缓存不存在或过期 → 重新 fetch

2. **验证缓存**（防止 stale data）：
```python
# Fetch 前 100 个字符对比
fresh_head = web_fetch(url, maxChars=100)
cached_head = cache[country][indicator].get('head_100_chars')

if fresh_head == cached_head:
    # 数据未变，使用缓存
    use_cache = True
else:
    # 数据已更新，重新 fetch 完整内容
    use_cache = False
```

3. **更新缓存**：
```json
{
  "country": "US",
  "indicator": "PMI",
  "fetched_at": "2026-03-20T15:00:00+08:00",
  "head_100_chars": "The S&P Global US Composite PMI dropped to 51.9...",
  "data": { ... }
}
```

---

### Step 3: Extract Data (带缓存优化)

```python
# 伪代码流程
cache_file = f"temp/macro_cache/{Country}_{Indicator}.json"

if os.path.exists(cache_file):
    cache = json.load(open(cache_file))
    if is_cache_fresh(cache):  # <24 hours
        # 验证缓存：fetch 前 100 字符对比
        fresh_head = web_fetch(url, maxChars=100)
        if fresh_head == cache['head_100_chars']:
            data = cache['data']  # 使用缓存
            skip_full_fetch = True

if not skip_full_fetch:
    data = web_fetch(url, extractMode='text', maxChars=1500)
    # 更新缓存
    update_cache(cache_file, data)
```

---

### Step 4: Detect Date from Summary

**从提取的段落中自动识别时间**，支持以下格式：

| 文本模式 | 识别结果 | 示例 |
|---------|---------|------|
| "in February 2026" | 2026-02 | "PMI fell to 51.6 in February 2026" |
| "in Q4 2025" | 2025-12 | "GDP grew 0.3% in Q4 2025" → 季度最后月份 |
| "in January" | 当前年份 -01 | 结合上下文推断年份 |
| "released on 2026-02-15" | 2026-02 | 发布日期 |
| "February reading" | 2026-02 | 当前年份 |

**日期识别脚本**：
```bash
python3 scripts/detect_date.py "<summary paragraph>"
```

**返回**：`YYYY-MM` 格式

---

### Step 5: Ensure Country Folder Exists

**⚠️ 关键步骤：笔记必须写入对应国家的笔记本**

```bash
# 笔记本列表（获取 folder_id）
ima_api "list_note_folder_by_cursor" '{"cursor": "0", "limit": 20}'

# 期望的笔记本结构：
# - US (folder6fd7dfe4c3d88488)
# - China (folder22193d7fb7e55cc8)
# - Japan (folder8e94e3efca419294)
# - EuroArea (folder653cfbe69cd7475b)
# - Bangladesh (folder8356d626be25a385)
# - SouthAfrica (folder33c2f9d193273d27)
# - Global (folder693ab9c25455821f)
```

**重要规则：根据国别写入对应的 IMA 笔记本**

- 创建笔记前，必须先获取目标国家的 folder_id
- IMA API 目前不支持在创建时直接指定 folder_id
- **变通方案**：创建笔记后，使用 IMA 客户端手动移动，或使用 IMA API 的 move 接口（如果支持）
- 禁止将笔记创建在默认位置后忘记移动
- 在汇报完成时，必须确认笔记已归属到正确的国家笔记本

**如果笔记本不存在**：提示用户手动在 IMA 客户端创建对应国家的笔记本。

---

### Step 6: Search for Existing IMA Note

**在写入之前，先搜索是否已存在对应笔记**：

```bash
# 搜索笔记标题
search_query="{Country} - {Indicator} - {Year}"
search_result=$(ima_api "search_note_book" "{
  \"search_type\": 0,
  \"query_info\": {\"title\": \"$search_query\"},
  \"start\": 0,
  \"end\": 20
}")

# 检查是否找到匹配的笔记
doc_id=$(echo "$search_result" | jq -r '.docs[0].doc.basic_info.docid // empty')

if [ -n "$doc_id" ]; then
  # 找到已有笔记 → 使用 append_doc 追加
  echo "找到已有笔记：$doc_id"
  use_append=true
else
  # 未找到 → 使用 import_doc 新建
  echo "未找到已有笔记，将创建新笔记"
  use_append=false
fi
```

---

### Step 7: Format Content for IMA

**IMA 笔记内容格式**（Markdown 格式，content_format=1）：

**重要：IMA 不支持子页面，所有子指标整合到单一笔记中**

```markdown
# {Country} - {Indicator} - {Year}

## 📊 {Indicator}

### {Sub-Indicator 1}

**{YYYY-MM}**. {Summary paragraph}

**{YYYY-MM}**. {Previous data paragraph}

### {Sub-Indicator 2}

**{YYYY-MM}**. {Summary paragraph}

---

*数据来源：Trading Economics | 更新时间：{current_datetime}*
*国家：{Country} | 指标：{Indicator} | 年份：{Year}*
```

**示例**（US - PMI - 2026）：

```markdown
# US - PMI - 2026

## 📊 PMI

### Composite PMI

**2026-02**. The S&P Global US Composite PMI dropped to 51.9 in February from 52.9 in the prior month...

**2026-01**. The S&P Global US Composite PMI rose to 52.9 in January...

### Manufacturing PMI

**2026-02**. The S&P Global US Manufacturing PMI fell to 51.6 in February...

### Services PMI

**2026-02**. The S&P Global US Services PMI fell to 51.7 in February...

---

*数据来源：Trading Economics | 更新时间：2026-03-20 22:00*
*国家：US | 指标：PMI | 年份：2026*
```

**子指标处理策略**：

| 指标类型 | 子指标 | 处理方式 |
|---------|--------|---------|
| **PMI** | Composite PMI, Manufacturing PMI, Services PMI | 整合到同一笔记，用 `###` 分隔 |
| **Inflation** | CPI, PPI, Core Inflation | 整合到同一笔记，用 `###` 分隔 |
| **GDP** | （无子指标） | 直接写入 |
| **Real Sector** | Industrial Production, Retail Sales, etc. | 整合到同一笔记，用 `###` 分隔 |

**好处**：
- 搜索一次看到所有相关数据
- 避免笔记碎片化（如 US-PMI 拆成 3 个笔记）
- 符合 IMA 的扁平结构
- 与 macro-archiver 的文档结构保持一致

---

### Step 8: Write to IMA Note

**重要：写入 IMA 后，必须同步保存到本地文件系统**

**Option A: Append to Existing Note**

```bash
# 追加内容到已有笔记（在末尾添加新月份数据）
ima_api "append_doc" "{
  \"doc_id\": \"$doc_id\",
  \"content_format\": 1,
  \"content\": \"\n\n**$detected_month**. $new_data_paragraph\"
}"
```

**Option B: Create New Note**

```bash
# 新建笔记
create_result=$(ima_api "import_doc" "{
  \"content_format\": 1,
  \"content\": \"$formatted_markdown_content\"
}")

# 获取返回的 doc_id
doc_id=$(echo "$create_result" | jq -r '.doc_id')
```

**Rules:**
- Never overwrite existing data
- If same month exists → Append as new paragraph
- Preserve all existing months' data
- **月份格式**：`**YYYY-MM**. `（黑体字 + 句点 + 空格，然后接正文）
- **不使用空占位符**（如 "*No data available yet*"），文档只包含实际数据

---

### Step 9: Save to Local File System

**本地存储结构**：

```
~/workspace/macro_data/
├── US/
│   ├── PMI.md
│   ├── GDP.md
│   └── Inflation.md
├── China/
│   ├── PMI.md
│   └── GDP.md
├── Japan/
│   └── PMI.md
...
```

**保存逻辑**：

```bash
# 1. 确保国家文件夹存在
mkdir -p ~/workspace/macro_data/{Country}/

# 2. 确定文件路径
file_path="~/workspace/macro_data/{Country}/{Indicator}.md"

# 3. 检查文件是否存在
if [ -f "$file_path" ]; then
    # 文件存在 → Append 模式
    echo -e "

## 更新时间：$(date +%Y-%m-%d %H:%M)
" >> "$file_path"
    echo "$new_data_content" >> "$file_path"
else
    # 文件不存在 → 创建新文件（包含完整结构）
    cat > "$file_path" << EOF
# {Country} - {Indicator}

## 📊 {Indicator}

$new_data_content

---
*数据来源：Trading Economics | 更新时间：$(date +%Y-%m-%d %H:%M)*
EOF
fi
```

**与 IMA 格式保持一致**：
- IMA 使用 Markdown → 本地也保存 Markdown
- 内容完全一致（可以直接从 IMA 写入内容复制）
- 更新时直接 append，不分析原文档内容

**好处**：
- 本地备份，防止 IMA 数据丢失
- 便于版本控制（可以用 git 管理）
- 便于离线查看和批量处理
- 与 IMA 互为备份

---

### Step 9: No Placeholder Policy (Token 优化)

**笔记中不保留空占位符**：

❌ **旧格式**（浪费 token）：
```markdown
### Composite PMI
#### 2026-01
*No data available yet.*
#### 2026-02
*No data available yet.*
```

✅ **新格式**（只包含实际数据）：
```markdown
### Composite PMI
**2026-02**. The S&P Global US Composite PMI dropped to 51.9 in February...
```

**好处：**
- 笔记更简洁（减少 60-80% 字符）
- 读取/写入 token 大幅减少
- 避免维护占位符的开销

---

## Token Efficiency

| Method | Chars/Page | Savings |
|--------|-----------|---------|
| Unrestricted | ~4,000 | - |
| Optimized | ~750 | ~80% |
| **With Cache + Append + Annual** | ~100 | **~97%** |

---

## Scripts

复用 macro-archiver 的脚本：
- `scripts/extract_macro_data.py` - 提取工具
- `scripts/detect_date.py` - 日期识别工具
- `scripts/cache_utils.py` - 缓存管理工具

新增 IMA 专用脚本：
- `scripts/ima_writer.py` - IMA 笔记写入工具

---

## References

复用 macro-archiver 的参考资料：
- `references/url-library-template.json` - URL 模板
- `references/document-structure-template.md` - 文档结构模板
- `references/date-patterns.md` - 日期识别规则详情
- `references/indicator-hierarchy.json` - 指标层级定义

---

## IMA Markdown Rendering Note

**重要**：IMA API 的 `get_doc_content` 在纯文本模式 (`target_content_format=0`) 下会移除换行符，但 **IMA 客户端应用会正确渲染 Markdown**。

- **写入时**：必须使用 `content_format=1` (Markdown)
- **读取时**：API 返回纯文本会移除换行（API 限制）
- **客户端显示**：IMA App/网页版会正确渲染 Markdown 格式

因此，笔记在 IMA 客户端中的显示效果应该是：
```
# US - PMI - 2026     ← 大标题

## PMI                ← 二级标题

### Composite PMI     ← 三级标题

**2026-02**. 数据段落   ← 粗体月份 + 正文
```

---

## Example

**User:** "更新美国 PMI 到 IMA"

**Agent:**
1. **Validate IMA credentials**: Check IMA_OPENAPI_CLIENTID and IMA_OPENAPI_APIKEY
2. **Check cache**: Read `temp/macro_cache/US_PMI.json`
3. **Validate cache**: Fetch first 100 chars, compare with cache
   - If match → Use cached data (skip full fetch)
   - If mismatch → Full fetch and update cache
4. **Extract data**: Fetch from TradingEconomics URL
5. **Detect dates:**
   - Composite PMI: "dropped to 51.9 in February" → **2026-02**
   - Manufacturing PMI: "fell to 51.6 in February of 2026" → **2026-02**
   - Services PMI: "fell to 51.7 in February of 2026" → **2026-02**
6. **Search IMA**: Search for note titled "US - PMI - 2026"
7. **Write to IMA**:
   - If note exists → Append new month data
   - If note not exists → Create new note with full content
8. **Write to IMA**:
   - If note exists → Append new month data
   - If note not exists → Create new note with full content
9. **Save to Local**:
   - Ensure folder `~/workspace/macro_data/US/` exists
   - Save to `US/PMI.md` (append mode if exists)
10. Report: "✅ US PMI data (February 2026) archived to IMA and local file"

---

## Error Handling

- **IMA credentials missing** → Stop and prompt user to configure
- **IMA API connection fails** → Retry once, then notify user
- **URL not found** → Ask user
- **Extraction fails** → Retry once
- **Date detection fails** → Use current month as fallback, notify user
- **Cache validation fails** → Full fetch and update cache
- **Note size limit exceeded** → Split into multiple append operations
- **Note not found** → Create new note instead of append

---

## IMA API Helper Function

**定义辅助函数统一调用格式**：

```bash
ima_api() {
  local endpoint="$1" body="$2"
  curl -s -X POST "https://ima.qq.com/openapi/note/v1/$endpoint" \
    -H "ima-openapi-clientid: $IMA_OPENAPI_CLIENTID" \
    -H "ima-openapi-apikey: $IMA_OPENAPI_APIKEY" \
    -H "Content-Type: application/json" \
    -d "$body"
}
```

---

## IMA Note Organization

**建议的笔记命名规范**：

```
{Country} - {Indicator} - {Year}
```

**示例**：
- `US - PMI - 2026`
- `China - GDP - 2026`
- `Global - Trade - 2026`

**好处**：
- 便于搜索（按国家、指标、年份筛选）
- 结构清晰，一目了然
- 与 macro-archiver 的文档命名保持一致

---

## Privacy Note

**IMA 笔记属于用户个人隐私数据**：
- 在群聊场景中只展示标题和摘要
- 禁止展示笔记正文内容
- 所有 API 调用使用用户自己的凭证
