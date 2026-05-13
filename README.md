# AI Daily Report Generator - AI日报自动生成器

> 每天自动抓取AI领域热门资讯，生成结构化Markdown日报。可直接发布到公众号/CSDN/知乎。

[![Python](https://img.shields.io/badge/Python-3.6%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## 为什么需要这个工具？

AI领域发展太快了！每天都有新论文、新模型、新工具发布。
- 技术博主需要持续输出内容，但找素材耗时
- AI从业者需要跟踪前沿，但信息源太分散
- 自媒体人需要每日热点，但整理太麻烦

这个工具帮你：
1. **自动抓取** 3大数据源的热门AI资讯
2. **AI摘要** 一键生成专业日报
3. **Markdown输出** 直接复制到公众号/CSDN/知乎

## 功能特点

- **3大数据源**
  - Hacker News - 全球技术社区热门
  - arXiv - 最新AI学术论文
  - GitHub Trending - 热门AI开源项目
- **AI智能摘要** - 接入DeepSeek API自动生成编辑摘要（可选）
- **本地降级** - 无API Key也能生成基础日报
- **智能缓存** - 1小时缓存，避免重复请求
- **关键词过滤** - 支持自定义关键词，精准筛选
- **中文支持** - 支持中文关键词，适合国内用户
- **零依赖** - 纯Python标准库，无需pip install

## 快速开始

### 1. 基础用法（无需API Key）

```bash
python ai_daily_report.py generate
```

输出文件：`ai_daily_20260514.md`

### 2. 自定义关键词

```bash
python ai_daily_report.py generate -k "GPT,LLM,agent,multimodal"
```

### 3. 中文关键词

```bash
python ai_daily_report.py generate --cn -k "大模型,AI Agent"
```

### 4. 指定数据源

```bash
# 只抓Hacker News和arXiv
python ai_daily_report.py generate -s "hackernews,arxiv"
```

### 5. AI增强摘要（需要DeepSeek API Key）

```bash
export DEEPSEEK_API_KEY="your-key"
python ai_daily_report.py generate -k "LLM,transformer"
```

## 使用示例

### 示例1：生成每日AI日报

```bash
python ai_daily_report.py generate --cn -o daily_report.md
```

生成的报告包含：
- AI编辑摘要（今日概览/重点解读/趋势洞察/推荐关注）
- Hacker News热门TOP15
- arXiv最新论文TOP15
- GitHub热门项目TOP15

### 示例2：预览数据（不生成报告）

```bash
python ai_daily_report.py preview
```

### 示例3：CI/CD自动发布

```yaml
# .github/workflows/daily-report.yml
name: AI Daily Report
on:
  schedule:
    - cron: '0 8 * * *'  # 每天早上8点
jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate Report
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
        run: python ai_daily_report.py generate --cn -o report.md
      - name: Publish
        run: |
          # 自动发布到你的平台
          python publish.py report.md
```

## 命令列表

| 命令 | 说明 |
|------|------|
| `generate` | 生成AI日报 |
| `preview` | 预览数据（不生成文件） |
| `stats` | 查看缓存统计 |

### generate 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-k, --keywords` | 关键词（逗号分隔） | AI内置关键词列表 |
| `--cn` | 包含中文关键词 | 否 |
| `-s, --sources` | 数据源（逗号分隔） | hackernews,arxiv,github |
| `-o, --output` | 输出文件路径 | ai_daily_YYYYMMDD.md |

## 报告示例

```markdown
# AI 日报 | 2026年05月14日 周三

> 每日AI领域精选资讯 | 关键词: artificial intelligence, machine learning, LLM
> 数据来源: Hacker News, arXiv, GitHub | 共 32 条

---

## AI 编辑摘要

### 今日概览
DeepSeek发布V4版本性能大幅提升，Meta开源新一代多模态模型...

### 重点解读
1. **DeepSeek-V4架构创新** - 采用了全新的MoE架构...
2. **arXiv论文: Efficient Attention** - 提出线性复杂度的注意力机制...
3. **GitHub: AI Agent Framework** - 新星项目3天获5k stars...

---

## 📰 Hacker News
### 1. DeepSeek V4 Outperforms GPT-4o...
### 2. ...

## 📄 arXiv
### 1. Efficient Linear Attention...
### 2. ...

## 💻 GitHub
### 1. awesome-ai-agents - ...
### 2. ...
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API密钥（可选，无则用本地摘要） |

## 定价

**免费版**: 本地摘要模式（无限使用）
**付费版**: 29元（DeepSeek AI增强摘要 + 季度更新 + 多平台自动发布）

适合：技术博主、AI从业者、自媒体运营者、知识付费创作者

## 系统要求

- Python 3.6+
- 网络连接（抓取数据源）
- DeepSeek API Key（可选，用于AI摘要）

## License

MIT License
