# 基于 CrewAI 的两阶段研究员 Agent 系统

本项目构建了标准的**两阶段协同研究架构**（Phase 1: 广度情报搜寻 -> Phase 2: 深度分析与事实核验），严格遵循最小权限原则（Least Privilege）进行工具隔离与调用限制。

---

## 架构概览

```
           用户输入 (Topic)
                 │
                 ▼
    ┌─────────────────────────┐
    │  Phase 1: Scout Agent   │ ◄── 允许工具：SerperDevTool (搜索), ScrapeWebsiteTool (抓取)
    │  (广度情报搜集与去噪)     │ ◄── 限制约束：max_iter=8, max_rpm=15, allow_delegation=False
    └────────────┬────────────┘
                 │  事实清单 & 引用链接 (经过 Guardrail 质量守卫校验)
                 ▼
    ┌─────────────────────────┐
    │ Phase 2: Analyst Agent  │ ◄── 严格工具隔离：仅允许 FileReadTool (阻断公网搜索)
    │  (深度交叉比对与研判)     │ ◄── 限制约束：max_iter=5, max_rpm=15, 交付强结构化 Pydantic 模型
    └────────────┬────────────┘
                 │
                 ▼
       结构化最终交付报告 (Markdown / JSON)
```

---

## 目录结构

```
.
├── config/
│   ├── agents.yaml           # Agent 角色、目标、背景与限流配置
│   └── tasks.yaml            # 任务描述、预期输出与流转关系
├── src/
│   └── craw/
│       ├── __init__.py
│       ├── crew.py           # CrewBase 编排、工具绑定与 Guardrail 守卫
│       └── models.py         # Pydantic 结构化输出模型
├── tests/
│   └── test_crew_setup.py    # 架构与工具权限限制自动化测试
├── .env.example              # 环境变量与 API 密钥模板
├── main.py                   # 运行入口
└── pyproject.toml            # uv 项目依赖配置
```

---

## 快速上手

### 1. 安装与环境准备

项目使用 `uv` 统一管理依赖：

```bash
# 复制环境变量模板并填入您的 API Key
cp .env.example .env
```

在 `.env` 中按需配置：
- `GEMINI_API_KEY` 或 `OPENAI_API_KEY`
- `SERPER_API_KEY`（可选，配置后自动激活 Google 搜索功能）

### 2. 运行架构与安全约束测试

验证两阶段 Agent 的工具隔离（Analyst 绝无搜索工具、调用轮次不超过阈值等）：

```bash
uv run python tests/test_crew_setup.py
```

### 3. 执行研究任务

#### 模式 A：标准两阶段 Crew 顺序执行
```bash
# 默认议题
uv run python main.py

# 指定议题
uv run python main.py "2026年企业级大模型微调与 RAG 架构的选型平衡"
```

#### 模式 B：带自愈质检把关的 Advanced Flow 模式
支持在阶段一信息不足时触发自动重试门禁，并在完成深度分析后**同时自动导出 Markdown 与专业排版 Word (.docx)** 到 `reports/`：
```bash
uv run python main.py --flow "2026年具身智能在柔性制造中的落地路径"
```
产出与归档说明（所有历史报告永久保留于独立归档文件夹，永不覆盖）：
- **历史归档目录**：`reports/archive/{YYYYMMDD_HHMMSS}_{课题名称}.docx` 和 `.md`
- **最新快捷镜像**：`reports/research_report.docx` 和 `reports/research_report.md`（始终指向最近一次执行结果，方便快捷查阅）




#### 可视化：生成工作流结构图
```bash
uv run python main.py --plot
# 将生成 flow_plot.html，可在浏览器中直观预览两阶段路由拓扑图
```

