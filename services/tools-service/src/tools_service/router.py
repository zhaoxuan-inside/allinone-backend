from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import get_db
from common.permissions import Roles, require_role
from tools_service.schemas import (
    Tool, ToolCreate, ToolUpdate,
    ToolListResponse, ToolDetailResponse,
    ToolCategory, ToolExecutionRequest, ToolExecutionResponse
)
from tools_service.service import ToolService

router = APIRouter(prefix="/tools", tags=["tools"])


def get_tool_service(db: AsyncSession = Depends(get_db)) -> ToolService:
    return ToolService(db)


@router.get("", response_model=ToolListResponse)
async def get_all_tools(
    tool_service: ToolService = Depends(get_tool_service)
):
    """获取所有工具列表"""
    return await tool_service.get_all_tools()


@router.get("/categories", response_model=List[ToolCategory])
async def get_categories(
    tool_service: ToolService = Depends(get_tool_service)
):
    """获取工具分类列表"""
    return await tool_service.get_categories()


@router.get("/category/{category}", response_model=ToolListResponse)
async def get_tools_by_category(
    category: str,
    tool_service: ToolService = Depends(get_tool_service)
):
    """按分类获取工具"""
    return await tool_service.get_tools_by_category(category)


@router.get("/search", response_model=ToolListResponse)
async def search_tools(
    keyword: str = Query(..., min_length=1),
    tool_service: ToolService = Depends(get_tool_service)
):
    """搜索工具"""
    return await tool_service.search_tools(keyword)


@router.get("/frontend", response_model=ToolListResponse)
async def get_frontend_tools(
    tool_service: ToolService = Depends(get_tool_service)
):
    """获取前端工具列表"""
    return await tool_service.get_frontend_tools()


@router.get("/backend", response_model=ToolListResponse)
async def get_backend_tools(
    tool_service: ToolService = Depends(get_tool_service)
):
    """获取后端工具列表"""
    return await tool_service.get_backend_tools()


@router.get("/{tool_id}", response_model=ToolDetailResponse)
async def get_tool_detail(
    tool_id: UUID,
    tool_service: ToolService = Depends(get_tool_service)
):
    """获取工具详情"""
    detail = await tool_service.get_tool_detail(tool_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Tool not found")
    return detail


@router.post("/{tool_id}/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    tool_id: UUID,
    request: ToolExecutionRequest,
    tool_service: ToolService = Depends(get_tool_service)
):
    """执行后端工具"""
    return await tool_service.execute_tool(tool_id, request.parameters)


@router.post("", response_model=Tool)
async def create_tool(
    tool_data: ToolCreate,
    _=Depends(require_role(Roles.ADMIN)),
    tool_service: ToolService = Depends(get_tool_service)
):
    """创建工具（管理员）"""
    return await tool_service.create_tool(tool_data)


@router.put("/{tool_id}", response_model=Tool)
async def update_tool(
    tool_id: UUID,
    tool_data: ToolUpdate,
    _=Depends(require_role(Roles.ADMIN)),
    tool_service: ToolService = Depends(get_tool_service)
):
    """更新工具（管理员）"""
    tool = await tool_service.update_tool(tool_id, tool_data)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool