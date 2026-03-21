# IMA Macro Archiver

自动从 TradingEconomics 提取宏观经济数据并归档到 IMA 笔记的工具。

## 功能特性

- 📊 **自动数据提取**：从 TradingEconomics 抓取宏观经济指标
- 📅 **智能日期检测**：自动识别数据对应的年份和月份
- 📝 **IMA 笔记归档**：将数据整理后写入 IMA 个人笔记
- 🔄 **增量更新**：支持定期更新已有数据
- 📁 **层级结构**：按年份 - 月份组织数据，便于检索

## 支持的宏观经济指标

### 全球主要经济体
- 🇺🇸 美国：GDP、CPI、失业率、利率、PMI 等
- 🇪🇺 欧元区：GDP、CPI、失业率等
- 🇨🇳 中国：GDP、CPI、PMI、贸易数据等
- 🇯🇵 日本：GDP、CPI、利率等
- 🇬🇧 英国：GDP、CPI、利率等

### 其他指标
- 大宗商品价格（原油、黄金等）
- 汇率数据
- 债券收益率

## 使用方法

### 前置条件

1. 已安装 OpenClaw
2. 已配置 IMA 笔记访问权限

### 运行方式

#### 方式一：通过 OpenClaw 命令

```bash
# 运行归档任务
openclaw skill run ima-macro-archiver
```

#### 方式二：通过自然语言指令

在 OpenClaw 对话中直接说：
- "帮我更新宏观经济数据"
- "归档最新的经济数据到 IMA"
- "更新美国 GDP 数据"

### 输出结构

数据按以下层级组织在 IMA 笔记中：

```
📁 宏观经济数据
├── 📁 2024
│   ├── 📄 2024-01 宏观经济数据
│   ├── 📄 2024-02 宏观经济数据
│   └── ...
├── 📁 2025
│   └── ...
└── ...
```

## 项目结构

```
ima-macro-archiver/
├── SKILL.md                    # Skill 定义文件
├── README.md                   # 本文件
├── scripts/
│   ├── extract_macro_data.py   # 数据提取主脚本
│   ├── detect_date.py          # 日期检测模块
│   ├── ima_writer.py           # IMA 写入模块
│   ├── cache_utils.py          # 缓存管理
│   ├── convert_feishu_doc.py   # 飞书文档转换
│   └── wiki_hierarchy.py       # 层级管理
└── references/
    ├── indicator-hierarchy.json # 指标层级定义
    ├── url-library-template.json # URL 库模板
    ├── date-patterns.md        # 日期模式库
    └── document-structure-template.md # 文档结构模板
```

## 配置说明

### 数据源配置

默认数据源为 TradingEconomics，可在脚本中配置：

```python
BASE_URL = "https://tradingeconomics.com"
```

### 缓存配置

数据会缓存在本地，避免重复抓取：

```bash
# 缓存目录
~/.openclaw/skills/ima-macro-archiver/cache/
```

## 定时任务（可选）

可以通过 cron 设置定期更新：

```bash
# 每月 1 号更新上月数据
0 9 1 * * openclaw skill run ima-macro-archiver
```

## 注意事项

1. **数据延迟**：宏观经济数据通常有 1-2 个月的发布延迟
2. **网络依赖**：需要访问 TradingEconomics 网站
3. **数据准确性**：建议与官方数据源交叉验证

## 技术栈

- Python 3.10+
- OpenClaw Skill Framework
- IMA API

## 开发说明

### 添加新指标

1. 在 `references/indicator-hierarchy.json` 中添加指标定义
2. 在 `scripts/extract_macro_data.py` 中实现提取逻辑
3. 测试并验证数据准确性

### 调试

```bash
# 启用详细日志
export DEBUG=1
python scripts/extract_macro_data.py
```

## License

MIT License

## Author

- GitHub: [@david-chi-zhang](https://github.com/david-chi-zhang)

## 更新日志

- **v1.0.0** (2026-03) - 初始版本
  - 实现基础数据提取功能
  - 支持 IMA 笔记归档
  - 支持日期自动检测
