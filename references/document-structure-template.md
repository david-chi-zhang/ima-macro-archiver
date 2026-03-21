# Macro Economic Data Archive - Document Structure

## File Structure (Annual + Indicator-based)

```
macro_data/
├── index.md                      # 全局索引
├── url_library.json              # URL 库
├── US_GDP_2026.md                # 按国家_指标_年命名
├── US_PMI_2026.md
├── US_Inflation_2026.md
├── China_GDP_2026.md
├── China_PMI_2026.md
└── ...
```

## Feishu Wiki Hierarchy

```
JVS Knowledge Base
└── Macro - 宏观经济数据索引 (root, node_token: Nku3wbMnTigBAikD0wAcj5bLnZe)
    ├── US - 2026 (parent)
    │   ├── US - GDP - 2026 (child)
    │   ├── US - PMI - 2026 (child)
    │   │   ├── Composite PMI
    │   │   ├── Manufacturing PMI
    │   │   └── Services PMI
    │   ├── US - Inflation - 2026 (child)
    │   └── US - Real Sector - 2026 (child)
    ├── China - 2026 (parent)
    │   ├── China - GDP - 2026 (child)
    │   └── China - PMI - 2026 (child)
    └── Japan - 2026 (parent)
        └── ...
```

## Parent Document Template (Index)

```markdown
# {Country} - {Year}

## 📊 经济指标数据

*宏观经济数据按指标分类，点击指标名称查看详情。*

---

### GDP
- [GDP](wiki_link_gdp)

### PMI

- [Composite PMI](wiki_link_composite)
- [Manufacturing PMI](wiki_link_manufacturing)
- [Services PMI](wiki_link_services)

### Inflation

- [CPI](wiki_link_cpi)
- [PPI](wiki_link_ppi)
- [Core Inflation](wiki_link_core)

### Real Sector

- [Industrial Production](wiki_link_ip)
- [Retail Sales](wiki_link_retail)
- [Consumer Confidence](wiki_link_confidence)
- [Unemployment](wiki_link_unemployment)

---

*最后更新：{date}*
```

## Child Document Template

```markdown
# {Country} - {Indicator} - {Year}

## {Indicator}

*数据来源：Trading Economics*

---

### Composite PMI

**2026-02**
The S&P Global US Composite PMI dropped to 51.9 in February from 53 in January...

**2026-01**
Previous month data paragraph...

### Manufacturing PMI

**2026-02**
The S&P Global US Manufacturing PMI fell to 51.6 in February...

### Services PMI

**2026-02**
The S&P Global US Services PMI fell to 51.7 in February...

---

*数据来源：Trading Economics | 更新时间：2026-03-20*
```

## Hierarchy Rules

### Parent Document (索引)
- **Title**: `{Country} - {Year}` (e.g., "US - 2026")
- **Parent**: "Macro - 宏观经济数据索引" (root)
- **Content**: Index with links to all child documents
- **Purpose**: Navigation hub for country-year data

### Child Document (子页面)
- **Title**: `{Country} - {Indicator} - {Year}` (e.g., "US - PMI - 2026")
- **Parent**: `{Country} - {Year}` (e.g., "US - 2026")
- **Content**: All sub-indicators for that category
- **Purpose**: Detailed data storage

### Indicator Grouping
```
PMI → Composite, Manufacturing, Services (all in one child doc)
Inflation → CPI, PPI, Core (all in one child doc)
Real Sector → IP, Retail, Confidence, Unemployment (all in one child doc)
```

## Key Rules

### ✅ DO: 层级结构
```
US - 2026 (parent)
└── US - PMI - 2026 (child)
    └── 所有 PMI 子指标数据
```

### ✅ DO: 按年度归档
```
US_PMI_2026.md  ← 2026 年所有 PMI 数据
US_PMI_2027.md  ← 2027 年所有 PMI 数据
```

### ❌ DON'T: 不要按季度
```
❌ US_PMI_2026Q1.md
❌ US_PMI_2026Q2.md
```

### ❌ DON'T: 不要空占位符
```markdown
### Composite PMI
#### 2026-01
*No data available yet.*  ← 不要这样写
```

### ✅ DO: 只包含实际数据
```markdown
### Composite PMI
**2026-02**
The S&P Global US Composite PMI dropped to 51.9...
```

## Why This Structure?

| Benefit | Description |
|---------|-------------|
| **Token Efficient** | Small documents (~500 chars vs ~8000) |
| **Clean Navigation** | Parent-child hierarchy in wiki |
| **Easy Updates** | Append to specific indicator doc |
| **Scalable** | New year = new parent doc |
| **Logical Grouping** | Related indicators together |

## Year Transition

**Current Year**: 2026

**Automatic Detection**:
- Default to current year documents
- When year changes (Jan 2027), create new parent: "US - 2027"
- Child docs automatically follow: "US - PMI - 2027"

**Manual Override**:
- User can specify: `更新美国 PMI 到 2027 年文档`
