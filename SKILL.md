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

### Step 1: Parse Request & Load URL Configuration

- **Country**: US, EuroArea, Japan, SouthAfrica, Bangladesh, Global, China
- **Indicator**: GDP, PMI, Inflation, RealSector, etc.
- **Year**: Current year (e.g., 2026)

---

#### 🔴 强制规则：URL 必须严格遵循 url-library-template.json

**⚠️ 重要教训 (2026-04-27 错误记录)**:

| 错误 | 后果 |
|------|------|
| 自行推断 URL（如 "应该是 /country/indicator"） | 使用了错误的数据类型（YoY vs MoM） |
| 使用"看起来合理"但不是配置的 URL | 美国工业生产：用了 YoY 数据，应该用 MoM |
| 假设某个 URL 是"标准"格式 | 南非零售销售：用了 MoM 数据，应该用 YoY |

**正确做法**:

```bash
# === Step 1.1: 读取 URL 配置（强制！）===
url_library="references/url-library-template.json"

if [ ! -f "$url_library" ]; then
    echo "❌ 未找到 URL 配置文件：$url_library"
    exit 1
fi

# === Step 1.2: 根据国家和指标提取正确的 URL ===
# 示例：US RealSector.IndustrialProduction
url=$(jq -r ".${Country}.RealSector.${Indicator} // empty" "$url_library")

# 如果第一层找不到，尝试直接查找（如 Inflation.CPI）
if [ -z "$url" ]; then
    url=$(jq -r ".${Country}.${Indicator} // empty" "$url_library")
fi

# === Step 1.3: 验证 URL 是否找到 ===
if [ -z "$url" ] || [ "$url" = "null" ]; then
    echo "❌ 未找到 ${Country} ${Indicator} 的 URL 配置"
    echo "请检查 $url_library 中是否包含该指标"
    exit 1
fi

echo "✅ 使用配置的 URL: $url"

# === Step 1.4: 使用配置的 URL 抓取数据 ===
data=$(web_fetch "$url" --extract-mode text --max-chars 2000)
```

---

#### 📋 URL 配置示例 (url-library-template.json)

```json
{
  "US": {
    "RealSector": {
      "IndustrialProduction": "https://tradingeconomics.com/united-states/industrial-production-mom",
      "RetailSales": "https://tradingeconomics.com/united-states/retail-sales"
    },
    "Inflation": { "CPI": "https://tradingeconomics.com/united-states/inflation-cpi" }
  },
  "SouthAfrica": {
    "RealSector": {
      "RetailSales": "https://tradingeconomics.com/south-africa/retail-sales-annual"
    }
  }
}
```

**注意 URL 命名规则**:
- `-mom` 后缀 = 月环比数据 (Month-over-Month)
- `-annual` 后缀 = 年同比数据 (Year-over-Year)
- 无后缀 = 通常是年同比或水平值

---

#### ✅ 执行前检查清单

- [ ] 已读取 `references/url-library-template.json`
- [ ] 已从配置中提取正确的 URL（非自行推断）
- [ ] 已验证 URL 存在且有效
- [ ] 已记录使用的 URL 到日志

**绝对禁止**:
- ❌ 自行推断 URL 结构
- ❌ 使用"看起来合理"但不是配置的 URL
- ❌ 假设某个 URL 是"标准"格式

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

**⚠️ 强制规则：先搜索→追加，找不到→新建（禁止直接创建！）**

**执行流程**：

```bash
# 1. 构建搜索关键词（按优先级尝试多个变体）
search_variants=(
  "{Country} - {Indicator} - {Year}"      # 标准格式
  "{Country} - {Indicator}"               # 不带年份
  "{Indicator} - {Year}"                  # 不带国家
)

# 2. 遍历搜索变体，找到第一个匹配的笔记
doc_id=""
for query in "${search_variants[@]}"; do
  search_result=$(ima_api "search_note_book" "{
    \"search_type\": 0,
    \"query_info\": {\"title\": \"$query\"},
    \"start\": 0,
    \"end\": 20
  }")
  
  # 检查搜索结果
  found_id=$(echo "$search_result" | jq -r '.data.docs[]? | select(.doc.basic_info.folder_id == "$target_folder_id") | .doc.basic_info.docid' | head -1)
  
  if [ -n "$found_id" ]; then
    doc_id="$found_id"
    echo "✅ 找到已有笔记：$doc_id (搜索词：$query)"
    break
  fi
done

# 3. 决策：追加 or 新建
if [ -n "$doc_id" ]; then
  # ✅ 找到已有笔记 → 必须使用 append_doc 追加
  echo "📝 将追加数据到已有笔记"
  use_append=true
else
  # 🆕 未找到 → 使用 import_doc 新建
  echo "🆕 未找到已有笔记，将创建新笔记"
  use_append=false
fi
```

**⚠️ 关键注意事项**：

| 场景 | 正确做法 | 错误做法 |
|------|---------|---------|
| 找到已有笔记 | 使用 `append_doc` 追加 | ❌ 用 `import_doc` 覆盖 |
| 未找到笔记 | 使用 `import_doc` 新建 + 指定 `folder_id` | ❌ 创建在默认位置 |
| 找到多个匹配 | 选择 folder_id 匹配的那个 | ❌ 随机选一个 |
| 笔记存在但 folder_id 错误 | 提示用户手动移动 | ❌ 忽略不管 |

**为什么这条规则重要**：
- 防止数据丢失（覆盖模式会删除历史数据）
- 避免笔记碎片化（同一指标多个笔记）
- 保持归档完整性（所有月份数据在一起）

---

### Step 7: Format Content for IMA

**IMA 笔记内容格式**（Markdown 格式，content_format=1）：

**重要：IMA 不支持子页面，所有子指标整合到单一笔记中**

---

#### ⚠️ 格式规范（强制遵守）

**子项名称格式**：
1. **单词之间必须有空格**：`Industrial Production` ✅ 不是 `IndustrialProduction` ❌
2. **使用黑体**：`**Industrial Production**`
3. **子项名称与月份之间必须有空行**

**月份格式**：
- **黑体 + 句点 + 空格**：`**2026-01**. `
- 后接正文内容

---

#### ✅ 正确格式示例

```markdown
# {Country} - {Indicator} - {Year}

## 📊 {Indicator}

**{Sub-Indicator Name}**

**{YYYY-MM}**. {Summary paragraph}

**{Sub-Indicator Name 2}**

**{YYYY-MM}**. {Summary paragraph}

---

*数据来源：Trading Economics | 更新时间：{current_datetime}*
*国家：{Country} | 指标：{Indicator} | 年份：{Year}*
```

#### 具体示例（Japan - RealSector - 2026）

```markdown
# Japan - RealSector - 2026

## 📊 Real Sector Indicators

**Industrial Production**

**2026-01**. Japan's industrial production rose 4.3% month-over-month in January 2026...

**Retail Sales**

**2026-01**. Retail sales in Japan rose 1.8% yoy in January 2026...

**Consumer Confidence**

**2026-02**. Japan's consumer confidence index rose to 40.0 in February 2026...

**Unemployment Rate**

**2026-01**. Japan's unemployment rate was at 2.7% in January 2026...

---

*数据来源：Trading Economics | 更新时间：2026-03-25*
*国家：Japan | 指标：RealSector | 年份：2026*
```

---

#### ❌ 错误格式（避免）

```markdown
# Japan - RealSector - 2026

## 📊 Real Sector Indicators

### IndustrialProduction     ← 错误：用了 ### 且名称内部无空格

**2026-01**. Japan's...     ← 错误：子项名称与月份之间无空行

### RetailSales             ← 错误：名称内部无空格

**2026-01**. Retail...
```

---

#### 子指标处理策略

| 指标类型 | 子指标 | 处理方式 |
|---------|--------|---------|
| **PMI** | Composite PMI, Manufacturing PMI, Services PMI | 整合到同一笔记，用 `**名称**` + 空行分隔 |
| **Inflation** | CPI, PPI, Core Inflation | 整合到同一笔记，用 `**名称**` + 空行分隔 |
| **GDP** | （无子指标） | 直接写入 |
| **Real Sector** | Industrial Production, Retail Sales, etc. | 整合到同一笔记，用 `**名称**` + 空行分隔 |

**好处**：
- 搜索一次看到所有相关数据
- 避免笔记碎片化（如 US-PMI 拆成 3 个笔记）
- 符合 IMA 的扁平结构
- 与 macro-archiver 的文档结构保持一致
- **格式清晰易读**（子项名称与内容有明显分隔）

---

### Step 8: Write to IMA Note

**⚠️ 强制规则：根据 Step 6 的搜索结果决定写入方式**

---

#### Option A: 追加到已有笔记（优先）

**适用场景**: Step 6 找到了已有笔记（`use_append=true`）

```bash
# 准备追加内容（只包含新数据，带分隔符）
append_content="

**{Sub-Indicator Name}**

**$detected_month**. $new_data_paragraph"

# 执行追加
ima_api "append_doc" "{
  \"doc_id\": \"$doc_id\",
  \"content_format\": 1,
  \"content\": $(echo "$append_content" | jq -Rs .)
}"

echo "✅ 已追加数据到笔记：$doc_id"
```

**注意事项**：
- 追加内容前加空行（`\n\n`），确保格式清晰
- 只追加新月份数据，不要重复已有内容
- 如果同月份已存在 → 作为新段落追加（不覆盖）

---

#### Option B: 创建新笔记（仅在未找到已有笔记时）

**适用场景**: Step 6 未找到已有笔记（`use_append=false`）

```bash
# 准备完整笔记内容（包含所有子指标）
create_result=$(ima_api "import_doc" "{
  \"content_format\": 1,
  \"content\": $(echo "$formatted_markdown_content" | jq -Rs .),
  \"folder_id\": \"$target_folder_id\"
}")

# 获取返回的 doc_id
doc_id=$(echo "$create_result" | jq -r '.data.note_id')

echo "✅ 已创建新笔记：$doc_id"
```

**注意事项**：
- 创建时必须指定 `folder_id`（确保归属到正确国家笔记本）
- 内容包含完整结构（标题 + 所有子指标）
- 创建后验证 folder_id 是否正确

---

#### 写入后验证（强制）

```bash
# 验证：读取笔记确认写入成功
verify_result=$(ima_api "get_doc_content" "{
  \"doc_id\": \"$doc_id\",
  \"target_content_format\": 0
}")

# 检查是否包含新数据
if echo "$verify_result" | grep -q "$detected_month"; then
  echo "✅ 验证通过：新数据已成功写入"
else
  echo "❌ 验证失败：新数据未找到，请检查"
  exit 1
fi
```

---

**核心原则**：

| 原则 | 说明 |
|------|------|
| **Never overwrite** | 永远不使用覆盖模式，保留所有历史数据 |
| **Append first** | 优先追加，只有在找不到已有笔记时才新建 |
| **Same month handling** | 如果同月份已存在 → 作为新段落追加（保留多个来源） |
| **Format consistency** | 月份格式：`**YYYY-MM**. `（黑体 + 句点 + 空格） |
| **No placeholders** | 不使用空占位符（如 "*No data available yet*"） |

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

---

## Changelog

### 2026-04-27 - URL 配置强制规则更新

**教训总结**（美国工业生产、南非零售销售数据错误事故）：

**问题**：
- ❌ 未读取 `url-library-template.json` 确认正确的 URL
- ❌ 自行推断 URL 结构（如 "应该是 /country/indicator"）
- ❌ 使用了错误的数据类型（YoY vs MoM）

**具体错误**:

| 国家 | 指标 | 应使用的 URL | 实际使用的 URL | 数据类型错误 |
|------|------|-------------|---------------|-------------|
| US | Industrial Production | `industrial-production-mom` | `industrial-production` | 应为 MoM，用了 YoY |
| South Africa | Retail Sales | `retail-sales-annual` | `retail-sales` | 应为 YoY，用了 MoM |

**后果**：
- **美国工业生产**: 报告 +0.7% YoY，正确数据为 **-0.5% MoM**（创 2024 年 9 月以来最大跌幅）
- **南非零售销售**: 报告 -1.0% MoM，正确数据为 **+1.6% YoY**（创 2024 年 9 月以来最弱增速）

**修正**：
- ✅ Step 1 强制要求先读取 `url-library-template.json`
- ✅ 添加 URL 提取和验证的代码示例
- ✅ 添加执行前检查清单
- ✅ 明确禁止自行推断 URL

**新规则**：
```
url-library-template.json 是唯一可信的 URL 来源
任何自行推断的 URL 都是错误的
```

**影响范围**：Step 1（URL 配置读取）

---

### 2026-04-19 - 强制搜索规则更新

**教训总结**（南非 Mining Production 更新事故）：

**问题**：
- ❌ 未先搜索已有笔记就直接创建新笔记
- ❌ 导致同一指标出现重复笔记（docid: 7440977723683962 和 7451553761885927）
- ❌ 需要事后删除重复笔记并重新追加

**修正**：
- ✅ Step 6 强制要求先搜索多个变体（标准格式 → 不带年份 → 不带国家）
- ✅ Step 8 明确区分追加模式（append_doc）和新建模式（import_doc）
- ✅ 添加验证步骤，确认写入成功后才汇报完成

**新规则**：
```
先搜索 → 追加（优先）
找不到 → 新建（仅当搜索无结果）
```

**影响范围**：Step 6（搜索逻辑）、Step 8（写入逻辑）

---

### 2026-03-25 - 格式规范更新

**用户反馈修正**：

1. **子项名称格式**：
   - ✅ 单词之间必须有空格：`Industrial Production`
   - ❌ 禁止连写：`IndustrialProduction`

2. **子项名称与月份之间**：
   - ✅ 必须有空行分隔
   - ❌ 禁止直接连接

3. **格式示例**：
   ```markdown
   **Industrial Production**
   
   **2026-01**. Japan's industrial production rose 4.3%...
   ```

**影响范围**：Step 7 (Format Content for IMA)

---
