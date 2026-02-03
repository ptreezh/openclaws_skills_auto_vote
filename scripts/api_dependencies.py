#!/usr/bin/env python3
"""
API 依赖注入
"""
from fastapi import Header, HTTPException, Depends
from typing import Optional
from scripts.did_auth import DIDAuth
from scripts.database.db import db

did_auth = DIDAuth()

async def get_current_agent(
    x_agent_did: Optional[str] = Header(None, alias="X-Agent-DID")
) -> dict:
    """
    获取当前认证的 Agent

    Args:
        x_agent_did: 请求头中的 DID

    Returns:
        Agent 信息

    Raises:
        HTTPException: 认证失败
    """
    if not x_agent_did:
        raise HTTPException(status_code=401, detail="Missing X-Agent-DID header")

    agent = await did_auth.get_agent(x_agent_did)

    if not agent:
        raise HTTPException(status_code=401, detail="Agent not found")

    # 更新最后活跃时间
    await did_auth.update_last_active(x_agent_did)

    return agent
