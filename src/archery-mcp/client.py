"""Archery API 客户端，封装认证、token 刷新和业务接口调用。"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TOKEN_EXPIRE_BUFFER_SECONDS = 30


@dataclass
class TokenPair:
    access: str = ""
    refresh: str = ""
    access_expires_at: float = 0.0

    @property
    def is_access_expired(self) -> bool:
        return time.time() >= (self.access_expires_at - TOKEN_EXPIRE_BUFFER_SECONDS)

    @property
    def has_refresh(self) -> bool:
        return bool(self.refresh)


@dataclass
class ArcheryClient:
    """Archery 平台 HTTP 客户端。

    支持 JWT 认证与自动 token 刷新。
    """

    base_url: str
    username: str = ""
    password: str = ""
    token: TokenPair = field(default_factory=TokenPair)
    _http: httpx.AsyncClient | None = field(default=None, repr=False)

    # JWT access token 默认有效期（秒），用于无法从响应中获取时的兜底
    _default_access_lifetime: int = 300

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self.base_url.rstrip("/"),
                timeout=30.0,
            )
        return self._http

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # ── 认证 ─────────────────────────────────────────────

    async def authenticate(self, username: str = "", password: str = "") -> dict[str, Any]:
        """使用用户名密码获取 JWT token 对 (access + refresh)。"""
        self.username = username or self.username
        self.password = password or self.password
        if not self.username or not self.password:
            raise ValueError("username 和 password 不能为空")

        http = await self._get_http()
        resp = await http.post(
            "/api/auth/token/",
            json={"username": self.username, "password": self.password},
        )
        resp.raise_for_status()
        data = resp.json()
        self.token = TokenPair(
            access=data["access"],
            refresh=data["refresh"],
            access_expires_at=time.time() + self._default_access_lifetime,
        )
        logger.info("认证成功: user=%s", self.username)
        return {"message": "认证成功", "username": self.username}

    async def refresh_token(self) -> dict[str, Any]:
        """使用 refresh token 刷新 access token。"""
        if not self.token.has_refresh:
            raise ValueError("没有可用的 refresh token，请先认证")

        http = await self._get_http()
        resp = await http.post(
            "/api/auth/token/refresh/",
            json={"refresh": self.token.refresh},
        )
        resp.raise_for_status()
        data = resp.json()
        self.token.access = data["access"]
        self.token.access_expires_at = time.time() + self._default_access_lifetime
        logger.info("Token 刷新成功")
        return {"message": "Token 刷新成功"}

    async def _ensure_auth(self) -> None:
        """确保持有有效的 access token，过期时自动刷新。"""
        if not self.token.access:
            raise ValueError("尚未认证，请先调用 authenticate")
        if self.token.is_access_expired and self.token.has_refresh:
            logger.info("Access token 已过期，尝试自动刷新...")
            await self.refresh_token()

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token.access}"}

    # ── 带自动重试的请求 ─────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """发送请求，遇到 401 时自动刷新 token 并重试一次。"""
        await self._ensure_auth()
        http = await self._get_http()
        headers = {**self._auth_headers(), **kwargs.pop("headers", {})}

        resp = await http.request(method, path, headers=headers, **kwargs)

        if resp.status_code == 401 and self.token.has_refresh:
            logger.info("收到 401 响应，尝试刷新 token 后重试...")
            await self.refresh_token()
            headers.update(self._auth_headers())
            resp = await http.request(method, path, headers=headers, **kwargs)

        resp.raise_for_status()
        return resp

    # ── 业务接口 ──────────────────────────────────────────

    async def list_workflows(
        self,
        workflow_id: int | None = None,
        workflow_status: str | None = None,
        workflow_name: str | None = None,
        engineer: str | None = None,
        instance_id: int | None = None,
        db_name: str | None = None,
        create_time_gte: str | None = None,
        create_time_lt: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """获取 SQL 上线工单清单。

        常见 workflow_status 取值:
          - workflow_manreviewing: 待审核
          - workflow_review_pass: 审核通过
          - workflow_timingtask: 定时执行
          - workflow_queuing: 排队中
          - workflow_executing: 执行中
          - workflow_finish: 执行完成
          - workflow_abort: 已终止
          - workflow_autoreviewwrong: 自动审核不通过
        """
        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
        }
        if workflow_id is not None:
            params["workflow_id"] = workflow_id
        if workflow_status:
            params["workflow__status"] = workflow_status
        if workflow_name:
            params["workflow__workflow_name__icontains"] = workflow_name
        if engineer:
            params["workflow__engineer"] = engineer
        if instance_id is not None:
            params["workflow__instance_id"] = instance_id
        if db_name:
            params["workflow__db_name"] = db_name
        if create_time_gte:
            params["workflow__create_time__gte"] = create_time_gte
        if create_time_lt:
            params["workflow__create_time__lt"] = create_time_lt

        resp = await self._request("GET", "/api/v1/workflow/", params=params)
        return resp.json()
