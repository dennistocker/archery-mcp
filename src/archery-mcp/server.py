"""Archery MCP Server — 通过 MCP 协议暴露 Archery SQL 审核平台的工具。"""

from __future__ import annotations

import json
import os
import logging

from mcp.server.fastmcp import FastMCP

from archery_mcp.client import ArcheryClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ARCHERY_BASE_URL = os.environ.get("ARCHERY_BASE_URL", "")
ARCHERY_USERNAME = os.environ.get("ARCHERY_USERNAME", "")
ARCHERY_PASSWORD = os.environ.get("ARCHERY_PASSWORD", "")

mcp = FastMCP(
    "Archery SQL Audit",
    instructions=(
        "Archery SQL 审核平台 MCP 工具集。"
        "使用前请先调用 get_auth_token 进行认证，"
        "然后即可调用 get_workflow 查询 SQL 上线工单。"
        "Token 过期时会自动刷新，也可手动调用 refresh_auth_token。"
    ),
)

_client: ArcheryClient | None = None


def _get_client() -> ArcheryClient:
    global _client
    if _client is None:
        if not ARCHERY_BASE_URL:
            raise ValueError(
                "请设置环境变量 ARCHERY_BASE_URL，例如 https://archery.example.com"
            )
        _client = ArcheryClient(
            base_url=ARCHERY_BASE_URL,
            username=ARCHERY_USERNAME,
            password=ARCHERY_PASSWORD,
        )
    return _client


@mcp.tool()
async def get_auth_token(
    username: str = "",
    password: str = "",
) -> str:
    """认证 Archery 平台，获取 JWT Token。

    如果已通过环境变量 ARCHERY_USERNAME / ARCHERY_PASSWORD 配置了凭证，
    可以不传参数直接调用。否则需要提供 username 和 password。

    Args:
        username: Archery 用户名（可选，优先使用传入值）
        password: Archery 密码（可选，优先使用传入值）

    Returns:
        认证结果信息
    """
    client = _get_client()
    result = await client.authenticate(username=username, password=password)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def refresh_auth_token() -> str:
    """手动刷新 Archery 的 access token。

    通常不需要手动调用——当 token 过期时系统会自动刷新。
    仅在需要强制刷新时使用。

    Returns:
        刷新结果信息
    """
    client = _get_client()
    result = await client.refresh_token()
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def get_workflow(
    workflow_id: int | None = None,
    workflow_status: str = "",
    workflow_name: str = "",
    engineer: str = "",
    instance_id: int | None = None,
    db_name: str = "",
    create_time_gte: str = "",
    create_time_lt: str = "",
    page: int = 1,
    page_size: int = 20,
) -> str:
    """获取 Archery SQL 上线工单清单。

    支持按多种条件过滤，所有筛选参数均为可选。
    传入 workflow_id 可查询单个工单的详细信息（包含 SQL 内容）。

    Args:
        workflow_id: 工单 ID 精确匹配（对应 Archery URL 中 /detail/{id}/ 的 id）
        workflow_status: 工单状态过滤。可选值:
            - workflow_manreviewing: 待审核
            - workflow_review_pass: 审核通过
            - workflow_timingtask: 定时执行
            - workflow_queuing: 排队中
            - workflow_executing: 执行中
            - workflow_finish: 执行完成
            - workflow_abort: 已终止
            - workflow_autoreviewwrong: 自动审核不通过
        workflow_name: 工单名称模糊搜索
        engineer: 提交人用户名精确匹配
        instance_id: 实例 ID 精确匹配
        db_name: 数据库名精确匹配
        create_time_gte: 创建时间起始（ISO 格式，如 2025-01-01T00:00:00）
        create_time_lt: 创建时间截止（ISO 格式）
        page: 页码，默认 1
        page_size: 每页条数，默认 20

    Returns:
        分页的工单列表 JSON
    """
    client = _get_client()
    result = await client.list_workflows(
        workflow_id=workflow_id,
        workflow_status=workflow_status or None,
        workflow_name=workflow_name or None,
        engineer=engineer or None,
        instance_id=instance_id,
        db_name=db_name or None,
        create_time_gte=create_time_gte or None,
        create_time_lt=create_time_lt or None,
        page=page,
        page_size=page_size,
    )
    return json.dumps(result, ensure_ascii=False, default=str)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
