# Archery MCP Server

Archery SQL 审核平台的 MCP (Model Context Protocol) 工具服务器。

## 功能

| 工具 | 说明 |
|---|---|
| `get_auth_token` | 使用用户名密码认证，获取 JWT Token |
| `refresh_auth_token` | 刷新 access token（通常自动完成） |
| `get_workflow` | 获取 SQL 上线工单清单，支持按状态、提交人等过滤 |

## 快速开始

### 前置依赖

仅需安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)：

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 方式一：从 GitHub 安装

无需 clone 代码，`uvx` 直接从 Git 仓库安装运行：

```json
{
  "mcpServers": {
    "archery": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/dennistocker/archery-mcp.git",
        "archery-mcp"
      ],
      "env": {
        "ARCHERY_BASE_URL": "https://archery.example.com",
        "ARCHERY_USERNAME": "your_username",
        "ARCHERY_PASSWORD": "your_password"
      }
    }
  }
}
```

> 如需指定版本，可在 URL 末尾加 `@v0.1.0`。

### 方式二：从源码运行

Clone 代码后，使用 `uv run` 运行：

```json
{
  "mcpServers": {
    "archery": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/archery-mcp", "archery-mcp"],
      "env": {
        "ARCHERY_BASE_URL": "https://archery.example.com",
        "ARCHERY_USERNAME": "your_username",
        "ARCHERY_PASSWORD": "your_password"
      }
    }
  }
}
```

> 将 `/path/to/archery-mcp` 替换为本项目的实际路径。

## 环境变量

| 环境变量 | 说明 | 必需 |
|---|---|---|
| `ARCHERY_BASE_URL` | Archery 平台地址，如 `https://archery.example.com` | 是 |
| `ARCHERY_USERNAME` | 登录用户名 | 否（可在调用时传入） |
| `ARCHERY_PASSWORD` | 登录密码 | 否（可在调用时传入） |

## 手动运行（调试用）

```bash
# uv 会自动创建隔离环境并安装依赖
uv run --directory /path/to/archery-mcp archery-mcp
```

## 工单状态说明

| 状态值 | 含义 |
|---|---|
| `workflow_manreviewing` | 待审核 |
| `workflow_review_pass` | 审核通过 |
| `workflow_timingtask` | 定时执行 |
| `workflow_queuing` | 排队中 |
| `workflow_executing` | 执行中 |
| `workflow_finish` | 执行完成 |
| `workflow_abort` | 已终止 |
| `workflow_autoreviewwrong` | 自动审核不通过 |
