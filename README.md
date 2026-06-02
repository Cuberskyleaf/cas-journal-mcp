# CAS Journal MCP

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Enabled-6e45d6)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)

MCP (Model Context Protocol) server for querying **Chinese Academy of Sciences (CAS) journal rankings**, **JCR Impact Factors**, and **Chinese domestic journal rankings (CSCD / PKU Core / CSSCI / AMI)** — designed for researchers who need quick, AI-assisted journal evaluation.

---

## ✨ Features

- 🔍 **Journal Search** — fuzzy search by name (English/Chinese), ISSN lookup — both WoS/CAS and CNKI domestic systems
- 📊 **Compare** — side-by-side comparison of multiple journals (CAS/JCR)
- 🏆 **Top Journals** — list CAS Top-tier (1区) journals by discipline
- 🇨🇳 **Chinese Journal Rankings** — CSCD / PKU Core / CSSCI / AMI status + CNKI impact factors
- ⚠️ **Warning List** — check if a journal is on the 2025 International Journal Warning List
- 🧠 **AI-Ready** — built on MCP for seamless integration with Claude and other LLM clients

## 📦 Data Sources

| Dataset | Description | Period |
|---------|-------------|--------|
| **FQBJCR2025** | CAS Journal Ranking (升级版) | 2025 |
| **JCR2024** | JCR Impact Factor | 2024 |
| **GJQKYJMD2025** | International Journal Warning List | 2025 |
| **CNKI Journals** | Chinese journal rankings (CSCD/PKU Core/CSSCI/AMI) + CNKI IF | 2023–2024 |

Data courtesy of [ShowJCR](https://github.com/hitfyd/ShowJCR) and [cnki-journal-info](https://github.com/doublessay/cnki-journal-info).

## 🚀 Quick Start

### Prerequisites

- Python ≥ 3.10
- `pip` or `uv`

### Install & Run

```bash
# Clone
git clone https://github.com/Cuberskyleaf/cas-journal-mcp.git
cd cas-journal-mcp

# Install dependencies
pip install -r requirements.txt

# Run the MCP server
python server.py
```

### Configure with Claude Code

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "cas-journal": {
      "command": "python",
      "args": ["path/to/cas-journal-mcp/server.py"]
    }
  }
}
```

## 🛠️ Available Tools

| Tool | Description | Example |
|------|-------------|---------|
| `search_journal` | Search WoS journals by name (CAS/JCR) | `"Nature"`, `"Remote Sensing"` |
| `search_by_issn` | Lookup WoS journal by ISSN | `"0028-0836"` |
| `compare_journals` | Compare multiple journals (CAS/JCR) | `"Nature, Science, Cell"` |
| `check_warning` | Check warning list status | `"某期刊"` |
| `get_top_journals` | List CAS Top journals by field | `"geography"`, `"计算机"` |
| `search_cn_journal` | Search Chinese journals (CSCD/PKU/CSSCI/AMI) | `"地理学报"`, `"经济研究"` |
| `search_cn_by_issn` | Lookup Chinese journal by ISSN | `"0375-5444"` |
| `get_cn_core_journals` | List Chinese core journals by field & system | `"地理", "cscd"`, `"经济", "cssci"` |

## 📋 Example Queries

```
> Search for "Remote Sensing of Environment"
[ Remote Sensing of Environment
   ISSN: 0034-4257
   WoS: SCIE
   [CAS] 中科院大类: 地球科学 | 1区 [Top]
      小类1: 遥感 | 1区
      小类2: 环境科学 | 1区
   [IF] JCR IF(2024): 12.3 | Q1 | Rank: 5/275
   [OA] OA: No | 评审: Peer-reviewed
```

### Chinese Journal Example

```
> Search for "地理学报" (Acta Geographica Sinica)
[ 地理学报
   ISSN: 0375-5444 | CN: 11-1856/P
   主办: 中国地理学会;中国科学院地理科学与资源研究所
   语种: 中文 | 周期: 月刊 | 创刊: 1934
   [国内分级] CSCD核心, 北大核心, CSSCI来源, EI
   [CNKI-IF] 复合IF: 9.437 | 综合IF: 6.936
   [学科] 哲学与人文科学;基础科学 | 自然地理学和测绘学;地理
```

## ⚠️ Disclaimer

- The data is sourced from publicly available third-party datasets and may contain errors or omissions
- CAS rankings are updated annually; users should verify against official sources for critical decisions
- This tool is for **research convenience** only — not a replacement for official CAS or Clarivate data

## 📄 License

MIT © [Cyanwoo Rain](https://github.com/Cuberskyleaf)

---

<br>

## 中文说明

### 简介

CAS Journal MCP 是一个基于 MCP (Model Context Protocol) 的期刊查询服务，可查询：
- 中国科学院期刊分区（新锐分区升级版）和 JCR 影响因子（国际/WoS 期刊）
- 中文期刊国内分级（CSCD / 北大核心 / CSSCI / AMI）和 CNKI 影响因子
方便研究者借助 AI 快速评估期刊。

### 数据来源

- 中科院分区表升级版 2025（FQBJCR2025）
- JCR 影响因子 2024（JCR2024）
- 国际期刊预警名单 2025（GJQKYJMD2025）
- CNKI 中文期刊数据集（CSCD/北大核心/CSSCI/AMI + CNKI影响因子）

数据来源于 [ShowJCR](https://github.com/hitfyd/ShowJCR) 和 [cnki-journal-info](https://github.com/doublessay/cnki-journal-info)。

### 功能

| 工具 | 说明 |
|------|------|
| `search_journal` | 按期刊名称搜索 WoS 期刊（CAS/JCR分区） |
| `search_by_issn` | 按 ISSN 查询 WoS 期刊 |
| `compare_journals` | 多刊对比（CAS/JCR） |
| `check_warning` | 查询是否在预警名单 |
| `get_top_journals` | 按学科列出中科院 Top 期刊 |
| `search_cn_journal` | 按名称搜索中文期刊（CSCD/北大核心/CSSCI/AMI） |
| `search_cn_by_issn` | 按 ISSN 查询中文期刊 |
| `get_cn_core_journals` | 按学科+分级系统列出中文核心期刊 |

### 使用

```bash
pip install -r requirements.txt
python server.py
```

在 Claude Code 的 MCP 配置中加入上述 JSON 即可使用。

### 免责声明

数据来源于公开的第三方数据集，可能存在误差或遗漏。中科院分区每年更新，关键决策请以官方数据为准。本工具仅供研究辅助使用。
