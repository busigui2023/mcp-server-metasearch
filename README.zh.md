# MCP Server Metasearch

[![CI](https://github.com/busigui2023/mcp-server-metasearch/actions/workflows/ci.yml/badge.svg)](https://github.com/busigui2023/mcp-server-metasearch/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![PyPI](https://img.shields.io/pypi/v/mcp-server-metasearch)](https://pypi.org/project/mcp-server-metasearch/)

[English](README.md) | **简体中文**

一个本地 MCP（Model Context Protocol）服务器，聚合了 **5 个提供商的 15 个网页搜索与提取工具**，通过统一接口暴露给 AI。每个工具都受开关和 API 密钥双重控制 —— AI 代理只能看到它实际能用的工具。

**状态**: v0.2.7 — 生产就绪，测试全覆盖（123 个测试，91% 覆盖率）。

## 为什么选择 MCP Server Metasearch？

无需为每个搜索提供商单独配置 MCP 服务器，metasearch 提供**统一接口**：

- **零配置工具暴露** — 只有 API 密钥有效的工具才对 AI 代理可见
- **插件架构** — 放入一个 Python 文件即可添加新提供商，无需修改框架
- **共享基础设施** — 连接池、响应缓存、启动诊断开箱即用

## 目录

- [快速开始](#快速开始)
- [核心特性](#核心特性)
- [部署指南](#部署指南)
  - [Claude Code](#claude-code)
  - [OpenClaw](#openclaw)
  - [Hermes Agent](#hermes-agent)
- [内置工具](#内置工具)
- [配置参考](#配置参考)
- [添加新工具](#添加新工具)
- [故障排除 FAQ](#故障排除-faq)
- [开发与测试](#开发与测试)

## 快速开始

### 1. 配置

```bash
mkdir -p ~/.config/mcp-server-metasearch
cp .env.example ~/.config/mcp-server-metasearch/.env
# 编辑 ~/.config/mcp-server-metasearch/.env 填入你的 API 密钥
```

### 2. 运行

**推荐 — 使用 `uvx`（无需安装）：**

```bash
uvx mcp-server-metasearch
```

或通过任意 MCP 客户端连接 — 参见下方[部署指南](#部署指南)。

<details>
<summary>备选：使用 pip 全局安装</summary>

```bash
pip install mcp-server-metasearch
mcp-server-metasearch
```

</details>

<details>
<summary>备选：从源码安装</summary>

```bash
git clone https://github.com/busigui2023/mcp-server-metasearch.git
cd mcp-server-metasearch
uv venv && uv pip install -e ".[dev]"
mcp-server-metasearch
```

</details>

## 核心特性

- **插件架构**: 新增或移除网页工具只需放入一个 Python 文件，无需修改框架代码。
- **双重验证**: 每个工具都需要 `TOOL_*_ENABLED=true` 和对应的 API 密钥同时满足才会暴露。
- **可选密钥支持**: 部分工具无需 API 密钥即可工作，其他则严格要求。
- **启动韧性**: 如果零工具可用，服务器会输出详细诊断报告并最多重试 3 次后放弃。
- **本地日志**: 所有运行时日志同时写入 stderr（stdio 传输安全）和 `logs/mcp-server-metasearch.log`。
- **连接池复用**: 所有工具共享 `httpx.AsyncClient`，消除每次请求的连接开销，并通过 `atexit` 实现优雅关闭。
- **响应缓存**: 内存 TTL 缓存（600 秒），注册表级别包裹 —— 工具代码零改动。
- **优化配置加载**: 环境文件每个进程生命周期仅读取一次，避免每次工具调用都重复磁盘 I/O。
- **精简协议握手**: 服务器不声明未使用的 `resources` 和 `prompts` 能力。这防止 MCP 客户端（如 Hermes）自动生成对应功能的包装器工具，确保 agent 的工具列表聚焦于 15 个实际搜索工具。

## 部署指南

### 前置条件

- Python 3.10+
- 已安装 [uv](https://docs.astral.sh/uv/)（提供 `uvx` 零安装运行）
- 需要启用的服务对应的 API 密钥

### 1. 配置

参见上方[快速开始](#快速开始)，然后继续配置你的 MCP 客户端。

### 2. 连接 MCP 客户端

> **注意**：推荐使用 `uvx` — 无需 `pip install`。`uvx` 首次运行时自动下载并缓存包，后续直接复用缓存。如果你从源码安装，请使用"从源码安装"选项。

#### Claude Code

**uvx（推荐）：**

```bash
claude mcp add metasearch -- uvx mcp-server-metasearch
```

<details>
<summary>或直接编辑 <code>~/.claude/settings.json</code></summary>

```json
{
  "mcpServers": {
    "metasearch": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-server-metasearch"]
    }
  }
}
```
</details>

**从源码安装：**

```bash
claude mcp add metasearch -- uv run --directory /absolute/path/to/mcp-server-metasearch mcp-server-metasearch
```

<details>
<summary>或直接编辑 <code>~/.claude/settings.json</code></summary>

```json
{
  "mcpServers": {
    "metasearch": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/mcp-server-metasearch",
        "mcp-server-metasearch"
      ]
    }
  }
}
```
</details>

重启 Claude Code（`/quit` 后重新进入）。运行 `/mcp` 验证服务器是否出现。

#### OpenClaw

**uvx（推荐）：**

```bash
openclaw mcp add metasearch --command uvx --arg mcp-server-metasearch
```

<details>
<summary>或直接编辑 <code>openclaw.json</code></summary>

```json
{
  "mcp": {
    "servers": {
      "metasearch": {
        "command": "uvx",
        "args": ["mcp-server-metasearch"],
        "transport": "stdio"
      }
    }
  }
}
```
</details>

**从源码安装：**

```bash
openclaw mcp add metasearch \
  --command uv \
  --arg run \
  --arg --directory \
  --arg /absolute/path/to/mcp-server-metasearch \
  --arg mcp-server-metasearch
```

<details>
<summary>或直接编辑 <code>openclaw.json</code></summary>

```json
{
  "mcp": {
    "servers": {
      "metasearch": {
        "command": "uv",
        "args": [
          "run",
          "--directory",
          "/absolute/path/to/mcp-server-metasearch",
          "mcp-server-metasearch"
        ],
        "transport": "stdio"
      }
    }
  }
}
```
</details>

运行 `openclaw mcp probe metasearch` 测试连接，无需启动完整对话。

#### Hermes Agent

**uvx（推荐）：**

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  metasearch:
    command: "uvx"
    args: ["mcp-server-metasearch"]
```

**从源码安装：**

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  metasearch:
    command: "uv"
    args:
      - "run"
      - "--directory"
      - "/absolute/path/to/mcp-server-metasearch"
      - "mcp-server-metasearch"
```

重启 Hermes 或运行 `hermes mcp list` 验证。使用 `hermes mcp test metasearch` 检查连接性和工具发现。

#### 手动测试

**uvx（推荐）：**

```bash
uvx mcp-server-metasearch
```

**从源码安装：**

```bash
uv run --directory /absolute/path/to/mcp-server-metasearch mcp-server-metasearch
```

如果没有工具被启用，你会看到诊断表格，进程以代码 1 退出。修复 `.env` 后重试。

## 故障排除 FAQ

### Q: 诊断表格显示所有工具都是 "Skipped (switch disabled)"，即使我已设为 true。

**A:** `.env` 文件必须位于 `~/.config/mcp-server-metasearch/.env`，而非项目根目录。服务器**不会**读取仓库内部的本地 `.env` 文件。检查路径并确保 `true` 后没有尾随空格。

### Q: 诊断表格显示 "Skipped (missing API key)"，但我已经添加了密钥。

**A:** 检查这些常见错误：
- `=` 号后的密钥值为空。
- 同一行有 `#` 注释截断了值。
- 密钥名称拼写错误（例如 `JINA_APIKEY` 而非 `JINA_API_KEY`）。
- `.env` 文件以某种方式保存了 Windows 换行符（`\r\n`）导致解析失败。

### Q: MCP 客户端提示 "MCP server metasearch failed to start" 或进程立即退出。

**A:** 这通常意味着零工具通过验证，服务器以代码 1 退出。查看客户端日志（stderr）中的诊断表格。如果看到重试消息（`Retry 1/3`、`Retry 2/3`），说明服务器按设计工作 —— 在第 3 次重试前修复 `.env`，否则客户端可能停止尝试。

### Q: 我启用了一些工具，但客户端只显示其中一部分。

**A:** 每个工具独立验证。缺失的工具可能未通过自身的开关或密钥检查。查看启动诊断 —— 表格列出了每个工具及被跳过的确切原因。常见情况：
- `JINA_API_KEY` 缺失 → 所有 jina 工具隐藏
- `TAVILY_API_KEY` 缺失 → 所有 tavily 工具隐藏
- 某个工具的开关设为 `false` → 该单个工具隐藏

由于 jina 工具共享同一个密钥，它们一起出现或隐藏。tavily 工具也共享同一个密钥。

### Q: `uv run python -m mcp_server_metasearch` 手动运行正常，但 MCP 客户端启动时失败。

**A:** MCP 客户端通常以不同的工作目录或环境启动服务器。确保：
- 使用 `--project /absolute/path/to/mcp-server-metasearch`，这样无论客户端的 CWD 如何，`uv` 都能找到 `pyproject.toml`。
- `.env` 路径 `~/.config/mcp-server-metasearch/.env` 使用**绝对主目录**，不依赖于工作目录。

### Q: 如何完全重置启动重试计数器？

**A:** 删除重试文件：

```bash
rm ~/.cache/mcp-server-metasearch/startup_retries
```

这在测试配置更改并希望重新开始时很有用。

### Q: 服务器由客户端启动时，日志在哪里？

**A:** 日志同时写入：

- **stderr**（MCP 安全，在客户端控制台可见）
- **`logs/mcp-server-metasearch.log`**（5 MB 轮转，保留 3 个备份）

如果客户端捕获 stderr，请在那里查看。如果没有，检查项目目录中的日志文件。注意：日志文件是相对于服务器工作目录创建的，所以如果客户端更改了 CWD，日志可能出现在意外位置。

### Q: 我可以不使用 `uv` 或 `uvx` 运行服务器吗？

**A:** 可以。使用 `pip install mcp-server-metasearch` 全局安装（建议在独立虚拟环境中以避免污染系统 Python），然后直接运行 `mcp-server-metasearch`。注意：某些 Linux 发行版（Ubuntu 23.04+）因 PEP 668 限制阻止全局 `pip install` — 此时请使用 `uvx` 或虚拟环境。

## 内置工具

**当前总计：5 个提供商的 15 个工具。**

不确定用哪个工具？以下是决策矩阵：

| 目标 | 推荐工具 | 原因 |
|------|---------|------|
| 读取已知 URL / PDF | `jina_reader`、`exa_contents` 或 `firecrawl_scrape` | 直接提取，干净的 markdown。Firecrawl 还支持 HTML/链接输出 |
| 通用网页搜索 | `exa_search`、`tavily_search`、`firecrawl_search` 或 `bocha_web_search` | 节省 token，丰富的过滤器。Firecrawl 增加图片/新闻搜索。Bocha：中文优化，国内网络 |
| 公司 / 人物查找 | `exa_search` 带 `category` | Exa 的索引分类（5000 万+ 公司，10 亿+ 人物） |
| 学术论文 | `exa_search` 带 `category="research paper"` 或 `firecrawl_search` 带 `categories=["research"]` | 1 亿+ 论文索引 |
| 快速事实核查 Q&A | `exa_answer` 或 `bocha_ai_search` 带 `answer=True` | 直接答案 + 引用。Bocha AI 搜索返回模态卡片 + AI 总结 |
| 批量 URL 提取 | `tavily_extract` 或 `firecrawl_map` + 选择性抓取 | Tavily：最多 20 个 URL。Firecrawl map：发现全站 URL，然后按需抓取 |
| 深度研究报告 | `tavily_research` | 异步多步综合，带引用 |
| 最快可能的搜索 | `exa_search` 带 `type="instant"` | ~250ms 延迟 |
| 网站 URL 发现 | `firecrawl_map` | 1 个积分映射整个站点结构 |
| 递归站点抓取 | `firecrawl_crawl` | 自动发现和抓取所有子页面。默认 10 页限制以保证安全 |
| GitHub 代码搜索 | `firecrawl_search` 带 `categories=["github"]` | 搜索仓库、issue、代码文档 |
| 中文内容 / 国内网络 | `bocha_web_search` 或 `bocha_ai_search` | DeepSeek 官方搜索供应商，中国优化，无需代理 |

### `jina_reader`

使用 [jina.ai Reader](https://r.jina.ai/) 从任意网页、PDF 或文档 URL 提取干净、LLM 友好的内容。

**何时使用**：AI 需要读取特定 URL、解析 PDF 链接，或从 JS 重型站点提取文章内容。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `url` | `str` | — | 目标网页或 PDF URL。 |
| `return_format` | `str` | `"markdown"` | 输出格式。`"markdown"`、`"text"` 或 `"html"`。 |
| `target_selector` | `str \| None` | `None` | CSS 选择器，仅提取匹配元素（例如 `article.main-content`）。 |
| `remove_selectors` | `str \| None` | `None` | 逗号分隔的 CSS 选择器，用于移除（例如 `nav, footer, .ads`）。 |
| `timeout` | `int` | `30` | 页面加载超时，单位秒（1–180）。 |

**API 要求**: 需要 `JINA_API_KEY`。

**示例流程**：
1. AI 收到关于博客文章的用户问题。
2. AI 调用 `jina_reader` 传入博客 URL。
3. 服务器请求 `https://r.jina.ai/http://<url>` 并返回干净的 Markdown。

---

### `jina_search`

使用 [jina.ai Search](https://s.jina.ai/) 搜索网页，获取 LLM 友好的结果及完整页面摘要。

**何时使用**：AI 需要当前网页信息、事实核查或多源摘要。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `query` | `str` | — | 搜索关键词或自然语言问题。 |
| `num_results` | `int` | `5` | 返回结果数量（1–20）。 |
| `site` | `str \| None` | `None` | 限制特定域名（例如 `reddit.com`）。 |
| `search_type` | `str` | `"web"` | `"web"`、`"news"` 或 `"images"`。 |
| `return_format` | `str` | `"markdown"` | 结果格式。`"markdown"`、`"text"` 或 `"html"`。 |

**API 要求**: 需要 `JINA_API_KEY`。

**示例流程**：
1. 用户问 "Python 3.14 有什么新特性？"
2. AI 调用 `jina_search` 带 `query="Python 3.14 new features"`。
3. 服务器返回最多 5 个结果，每个含标题、URL 和完整内容摘要。

---

### `jina_deepsearch`

使用 [jina.ai DeepSearch](https://deepsearch.jina.ai/) 对复杂主题执行多步研究。将网页搜索、页面阅读和推理整合为带引用来源的单一综合答案。

**何时使用**：问题宽泛或探索性（例如 "2026 年 RAG 向量数据库对比"）。DeepSearch 自主搜索多个来源，阅读并综合报告。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `query` | `str` | — | 研究问题或主题。越具体效果越好。 |
| `max_tokens` | `int` | `4096` | 响应中的最大 token 数。 |

**API 要求**: 需要 `JINA_API_KEY`。

**示例流程**：
1. 用户问 "Weaviate、Qdrant 和 Milvus 用于生产 RAG 的权衡是什么？"
2. AI 调用 `jina_deepsearch` 传入完整问题。
3. 服务器发送查询到 `https://deepsearch.jina.ai/v1/chat/completions`。
4. 响应是带内联引用的结构化研究报告。

---

### `tavily_search`

使用 [Tavily](https://tavily.com/) 搜索网页，支持细粒度过滤器、相关性评分和可选 AI 生成答案。

**何时使用**：需要精确搜索，带时间范围过滤、域名限制、国家 boosting 或 AI 生成摘要答案。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `query` | `str` | — | 搜索关键词或自然语言问题。 |
| `search_depth` | `str` | `"basic"` | `"basic"`、`"fast"`、`"advanced"`（2 积分）或 `"ultra-fast"`。 |
| `max_results` | `int` | `5` | 返回结果数量（0–20）。 |
| `topic` | `str` | `"general"` | `"general"`、`"news"` 或 `"finance"`。 |
| `time_range` | `str \| None` | `None` | `"day"`、`"week"`、`"month"` 或 `"year"`。 |
| `include_answer` | `bool` | `False` | 包含查询的 LLM 生成答案。 |
| `include_raw_content` | `bool` | `False` | 每个结果包含完整清洗后的页面内容。 |
| `include_images` | `bool` | `False` | 包含搜索结果中的图片。 |
| `include_favicon` | `bool` | `False` | 每个结果包含 favicon URL。 |
| `include_domains` | `list[str] \| None` | `None` | 限制结果域名（最多 300 个）。 |
| `exclude_domains` | `list[str] \| None` | `None` | 排除结果域名（最多 150 个）。 |

**API 要求**: 需要 `TAVILY_API_KEY`。每月 1000 免费积分。

**示例流程**：
1. 用户问 "这周 AI 发生了什么？"
2. AI 调用 `tavily_search` 带 `query="AI news"`、`topic="news"`、`time_range="week"`、`include_answer=true`。
3. 服务器返回排序结果及简明的 AI 生成答案。

---

### `tavily_extract`

使用 [Tavily Extract](https://tavily.com/) 从一个或多个 URL 提取干净、LLM 友好的内容。支持批量提取和查询引导的块重排序。

**何时使用**：你已经知道 URL 并想批量提取内容，或想要查询相关块而非完整页面。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `urls` | `str \| list[str]` | — | 单个 URL 或 URL 列表。 |
| `query` | `str \| None` | `None` | 重排序块的用户意图。 |
| `extract_depth` | `str` | `"basic"` | `"basic"` 或 `"advanced"`（表格、嵌入内容）。 |
| `return_format` | `str` | `"markdown"` | `"markdown"` 或 `"text"`。 |

**API 要求**: 需要 `TAVILY_API_KEY`。

**示例流程**：
1. AI 从之前的搜索中找到 3 个相关 URL。
2. AI 调用 `tavily_extract` 带 `urls=[url1, url2, url3]`。
3. 服务器返回所有三个页面的干净 markdown。

---

### `tavily_research`

使用 [Tavily Research](https://tavily.com/) 执行全面、多步研究。执行多次搜索、分析来源并生成带引用的研究报告。

**何时使用**：问题宽泛，需要带引用的综合报告（例如 "2026 年云提供商 ML 工作负载对比"）。积分消耗高于单次搜索。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `input` | `str` | — | 要调查的研究任务或问题。 |
| `model` | `str` | `"auto"` | `"mini"`、`"pro"` 或 `"auto"`（默认）。 |
| `citation_format` | `str` | `"numbered"` | `"numbered"`、`"mla"`、`"apa"` 或 `"chicago"`。 |

**API 要求**: 需要 `TAVILY_API_KEY`。Research 消耗的积分显著高于单次搜索，因为它运行多次内部搜索 + 提取 + 综合步骤。

**示例流程**：
1. 用户问 "Weaviate、Qdrant 和 Milvus 用于生产 RAG 的权衡是什么？"
2. AI 调用 `tavily_research` 传入完整问题。
3. 服务器提交异步研究任务并轮询直到完成。
4. 响应是带编号引用和来源列表的结构化研究报告。

---

### `exa_search`

使用 [Exa](https://exa.ai/) 搜索网页，一个为 LLM 优化的搜索引擎。默认返回高度相关的摘录（highlights），节省 10 倍 token。支持分类过滤器和深度推理模式。

**何时使用**：需要节省 token 的搜索结果、公司/人物/研究论文分类过滤，或最快搜索延迟（`instant` ~250ms）。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `query` | `str` | — | 自然语言搜索查询。 |
| `type` | `str` | `"auto"` | `"auto"`、`"fast"`、`"instant"`、`"deep-lite"`、`"deep"`、`"deep-reasoning"`。 |
| `num_results` | `int` | `10` | 结果数量（1–100）。 |
| `category` | `str \| None` | `None` | `"company"`、`"people"`、`"research paper"`、`"news"`、`"personal site"`、`"financial report"`。 |
| `content_mode` | `str` | `"highlights"` | `"highlights"`（默认）、`"text"` 或 `"summary"`。 |
| `include_domains` | `list[str] \| None` | `None` | 白名单域名（最多 1200 个）。 |
| `exclude_domains` | `list[str] \| None` | `None` | 黑名单域名（最多 1200 个）。不支持 `company`/`people`。 |
| `max_age_hours` | `int \| None` | `None` | `0`=始终实时抓取，`-1`=仅缓存。 |

**API 要求**: 需要 `EXA_API_KEY`。

**示例流程**：
1. 用户问 "找美国农业科技的 A 轮公司。"
2. AI 调用 `exa_search` 带 `query="agtech companies US Series A"`、`category="company"`、`content_mode="highlights"`。
3. 服务器返回最多 10 个公司页面及关键摘录。

---

### `exa_contents`

使用 [Exa Contents](https://exa.ai/) 从一个或多个 URL 提取干净、LLM 就绪的内容。处理 JS 渲染页面、PDF 和复杂布局。支持子页面抓取。

**何时使用**：你已经知道 URL 并想提取内容，可选抓取链接子页面。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `urls` | `str \| list[str]` | — | 单个 URL 或 URL 列表。 |
| `content_mode` | `str` | `"text"` | `"text"`（完整页面）、`"highlights"` 或 `"summary"`。 |
| `max_age_hours` | `int \| None` | `None` | 内容新鲜度控制。 |
| `subpages` | `int` | `0` | 每个 URL 抓取的子页面数。 |
| `subpage_target` | `list[str] \| None` | `None` | 优先子页面的关键词。 |

**API 要求**: 需要 `EXA_API_KEY`。

**示例流程**：
1. AI 找到一个相关文档 URL。
2. AI 调用 `exa_contents` 带 `urls="https://docs.example.com"`、`subpages=10`、`subpage_target=["api", "reference"]`。
3. 服务器返回根页面内容加上最多 10 个链接子页面。

---

### `exa_answer`

获取由 [Exa](https://exa.ai/) 搜索结果提供信息的直接 LLM 答案。适合快速事实查找。

**何时使用**：需要特定问题的简明答案，而非搜索结果列表。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `query` | `str` | — | 要回答的问题。 |
| `text` | `bool` | `False` | 引用中包含完整来源文本。 |

**API 要求**: 需要 `EXA_API_KEY`。

**示例流程**：
1. 用户问 "SpaceX 最新估值是多少？"
2. AI 调用 `exa_answer` 传入问题。
3. 服务器返回 "3500 亿美元" 加引用来源。

---

### `firecrawl_scrape`

使用 [Firecrawl](https://firecrawl.dev) 从任意网页提取干净、LLM 就绪的内容。支持多种输出格式和动态内容渲染。

**何时使用**：AI 需要从已知 URL 精确提取内容，尤其是 JS 渲染站点，或想要 HTML/链接除 markdown 外。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `url` | `str` | — | 目标网页或 PDF URL。 |
| `formats` | `list[str]` | `["markdown"]` | 输出格式：`"markdown"`、`"html"`、`"links"`。 |
| `only_main_content` | `bool` | `True` | 排除导航、广告、页脚。 |
| `timeout` | `int` | `30000` | 页面加载超时，单位毫秒。 |
| `wait_for` | `int` | `0` | 动态内容等待时间（毫秒）。 |

**API 要求**: 需要 `FIRECRAWL_API_KEY`。

---

### `firecrawl_search`

使用 Firecrawl 搜索网页并获取结构化内容。支持网页、新闻和图片搜索及专业分类过滤。

**何时使用**：AI 需要图片结果、新闻结果，或按 GitHub/研究论文/PDF 分类过滤。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `query` | `str` | — | 自然语言搜索查询。 |
| `limit` | `int` | `5` | 每来源类型结果数（1–50）。 |
| `sources` | `list[str]` | `["web"]` | 结果类型：`"web"`、`"news"`、`"images"`。 |
| `categories` | `list[str]` | `None` | 过滤器：`"github"`、`"research"`、`"pdf"`。 |
| `include_domains` | `list[str]` | `None` | 限制这些域名。 |
| `exclude_domains` | `list[str]` | `None` | 排除这些域名。 |
| `scrape_content` | `bool` | `False` | 每个结果获取完整 markdown（额外积分）。 |

**API 要求**: 需要 `FIRECRAWL_API_KEY`。

**成本说明**: 每 10 个搜索结果 2 积分。`scrape_content=True` 每个结果页面增加 1 积分。

---

### `firecrawl_map`

快速发现网站上的所有 URL。返回完整链接列表及标题和描述。

**何时使用**：AI 想在决定阅读哪些页面前探索站点结构，或需要在大型站点上找到特定页面。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `url` | `str` | — | 要映射的网站。 |
| `limit` | `int` | `100` | 最大返回 URL 数（1–10,000）。 |
| `search` | `str` | `None` | 站点内关键词过滤。 |

**API 要求**: 需要 `FIRECRAWL_API_KEY`。

**成本说明**: 每次调用固定 1 积分，无论 URL 数量。

---

### `firecrawl_crawl`

递归抓取网站，自动发现和抓取所有可达子页面。

**何时使用**：AI 需要摄入整个文档站点、博客或任何多页资源。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `url` | `str` | — | 开始抓取的 URL。 |
| `limit` | `int` | `10` | 最大抓取页数（1–100）。**默认保守**以控制积分消耗。 |
| `max_discovery_depth` | `int` | `None` | 距起始 URL 的最大链接跳数。`None`=无限制。 |
| `include_paths` | `list[str]` | `None` | 包含路径的正则模式。 |
| `exclude_paths` | `list[str]` | `None` | 排除路径的正则模式。 |
| `allow_subdomains` | `bool` | `False` | 跟踪子域名链接。 |
| `formats` | `list[str]` | `["markdown"]` | 每页输出格式。 |

**API 要求**: 需要 `FIRECRAWL_API_KEY`。

**成本说明**: 每抓取 1 页 1 积分。默认 `limit=10` = 最多 10 积分。

---

### `bocha_web_search`

使用 [Bocha AI](https://www.bochaai.com/) 搜索网页，一个为 DeepSeek 网页搜索提供动力的中国优化搜索引擎。返回干净、结构化的结果，含网页标题、URL、摘要、站点信息和可选 AI 摘要。

**何时使用**：AI 需要搜索中文内容、访问国内网站，或需要一个无需代理即可可靠工作的搜索工具。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `query` | `str` | — | 自然语言搜索查询。 |
| `count` | `int` | `5` | 结果数量（1–50）。 |
| `freshness` | `str` | `None` | 时间过滤器：`oneDay`、`oneWeek`、`oneMonth`、`oneYear`、`noLimit` 或 `YYYY-MM-DD..YYYY-MM-DD`。 |
| `summary` | `bool` | `False` | 每个结果包含 AI 生成摘要。 |
| `include_domains` | `list[str]` | `None` | 仅返回这些域名的结果。 |
| `exclude_domains` | `list[str]` | `None` | 排除这些域名的结果。 |

**API 要求**: 需要 `BOCHA_API_KEY`。

**成本说明**: 每次调用 ¥0.036。个人使用有免费 tier。

---

### `bocha_ai_search`

使用 Bocha AI 的高级 AI 驱动搜索。返回网页结果加结构化模态卡片（天气、百科、股票、火车时刻表、医疗信息等）和可选 AI 生成答案及后续问题。

**何时使用**：AI 需要结构化数据提取（例如 "北京天气如何？"、"阿里巴巴股价"），或想要 AI 生成摘要答案伴随搜索结果。

**参数**：

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `query` | `str` | — | 自然语言搜索查询。 |
| `count` | `int` | `5` | 网页结果数量（1–50）。 |
| `freshness` | `str` | `None` | 时间过滤器（与网页搜索相同）。 |
| `answer` | `bool` | `False` | 包含 AI 生成摘要答案和后续问题。 |

**API 要求**: 需要 `BOCHA_API_KEY`。

**成本说明**: 每次调用 ¥0.060。`answer=True` 时返回模态卡片 + AI 答案。

---

## 配置参考

### `.env` 完整示例

```bash
# ── Jina AI ──
JINA_API_KEY=jina_xxxxxxxxxxxxxxxxxxxxxxxx
TOOL_JINA_READER_ENABLED=true
TOOL_JINA_SEARCH_ENABLED=true
TOOL_JINA_DEEPSEARCH_ENABLED=true

# ── Tavily ──
# TAVILY_API_KEY=tvly-xxxxxxxx
# TOOL_TAVILY_SEARCH_ENABLED=true
# TOOL_TAVILY_EXTRACT_ENABLED=true
# TOOL_TAVILY_RESEARCH_ENABLED=true

# ── Exa ──
# EXA_API_KEY=your_exa_api_key_here
# TOOL_EXA_SEARCH_ENABLED=true
# TOOL_EXA_CONTENTS_ENABLED=true
# TOOL_EXA_ANSWER_ENABLED=true

# ── Firecrawl ──
# FIRECRAWL_API_KEY=fc-xxxxxxxxxxxxxxxx
# TOOL_FIRECRAWL_SCRAPE_ENABLED=true
# TOOL_FIRECRAWL_SEARCH_ENABLED=true
# TOOL_FIRECRAWL_MAP_ENABLED=true
# TOOL_FIRECRAWL_CRAWL_ENABLED=true

# ── 博查 Bocha AI ──
# BOCHA_API_KEY=sk-xxxxxxxxxxxxxxxx
# TOOL_BOCHA_WEB_SEARCH_ENABLED=true
# TOOL_BOCHA_AI_SEARCH_ENABLED=true

```

### 双重验证如何工作

对于每个发现的工具，服务器在启动时检查两个条件：

1. **开关检查**: `TOOL_<NAME>_ENABLED` 必须是 `true`。
2. **密钥检查**: `.env` 中所有 `required_env_vars` 必须存在且非空。

两者都通过，工具才会被注册。如果某个工具任一检查失败，它会出现在启动诊断表格中并附带确切原因。

## 开发与测试

### 运行测试

```bash
uv run pytest tests/ -v
```

### 查看日志

运行时日志写入：

- **stderr**（MCP 安全，在客户端控制台可见）
- **`logs/mcp-server-metasearch.log`**（5 MB 轮转，保留 3 个备份）

```bash
tail -f logs/mcp-server-metasearch.log
```

### 启动诊断

如果没有工具被注册，服务器会打印诊断表格到 stderr：

```
[MCP-Metasearch] STARTUP DIAGNOSTICS
═══════════════════════════════════════════════════════════════════
Environment file: /home/<user>/.config/mcp-server-metasearch/.env
Retry attempt: 1/3

┌────────────────────┬─────────┬─────────────────┬─────────────────────────────┐
│ Tool               │ Switch  │ API Key         │ Result                      │
├────────────────────┼─────────┼─────────────────┼─────────────────────────────┤
│ jina_reader        │ OFF     │ JINA_API_KEY    │ Skipped (switch disabled)   │
│ jina_search        │ ON      │ MISSING         │ Skipped (missing API key)   │
└────────────────────┴─────────┴─────────────────┴─────────────────────────────┘
```

## 添加新工具

1. 创建 `src/mcp_server_metasearch/tools/my_tool.py`。
2. 继承 `BaseTool`：

```python
from mcp_server_metasearch.tools.base import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "这个工具做什么。"
    required_env_vars = ["MY_API_KEY"]   # 或 [] 如果不需要密钥
    enabled_env_var = "TOOL_MY_TOOL_ENABLED"

    async def call(self, param: str) -> str:
        ...
```

3. 将密钥和开关添加到 `~/.config/mcp-server-metasearch/.env`。
4. 重启 MCP 客户端。工具会被自动发现 —— 无需编辑 `server.py` 或 `tool_registry.py`。

## 项目结构

```
mcp-server-metasearch/
├── .env.example              # 配置模板
├── pyproject.toml            # 包元数据 & 依赖
├── scripts/                  # 各提供商端到端冒烟测试
├── src/mcp_server_metasearch/
│   ├── server.py             # FastMCP 实例 & 启动流程
│   ├── tool_registry.py      # 自动发现、双重验证 & 缓存包裹
│   ├── config.py             # .env 加载（单次读取）& pydantic-settings
│   ├── http_client.py        # 共享 httpx.AsyncClient，带优雅关闭
│   ├── cache.py              # 内存 TTL 响应缓存
│   ├── diagnostics.py        # 启动失败报告
│   ├── retry.py              # 持久化重试计数器
│   └── tools/                # 每个工具一个文件（插件架构）
│       ├── base.py           # BaseTool 抽象类
│       ├── formatting.py     # 共享格式化工具
│       ├── jina_*.py         # Jina AI 工具（reader, search, deepsearch）
│       ├── tavily_*.py       # Tavily 工具（search, extract, research）
│       ├── exa_*.py          # Exa 工具（search, contents, answer）
│       ├── firecrawl_*.py    # Firecrawl 工具（scrape, search, map, crawl）
│       └── bocha_*.py        # Bocha 工具（web_search, ai_search）
└── tests/                    # 单元测试（123 个测试，91% 覆盖率）
```

## 致谢

本项目集成了以下搜索与提取服务：

- [Jina AI](https://jina.ai/) — 网页阅读与搜索
- [Tavily](https://tavily.com/) — 搜索、提取与研究
- [Exa](https://exa.ai/) — 面向 LLM 的语义搜索
- [Firecrawl](https://firecrawl.dev/) — 网页抓取与爬取
- [博查 AI](https://open.bochaai.com/) — 中文优化搜索

用户需要自行申请这些服务的 API 密钥。本项目不提供或分发任何 API 密钥。

## 许可证

MIT 许可证 — 详见 [LICENSE](LICENSE)。

## 贡献

参见 [CONTRIBUTING.md](CONTRIBUTING.md) 了解开发环境搭建和贡献指南。
