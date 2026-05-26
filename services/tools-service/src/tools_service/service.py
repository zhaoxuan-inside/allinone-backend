from typing import Optional, List, Dict, Any
from uuid import UUID
import time

from sqlalchemy.ext.asyncio import AsyncSession

from src.tools_service.entities import Tool
from src.tools_service.repository import ToolRepository, ToolCategoryRepository, ToolUsageLogRepository
from src.tools_service.schemas import (
    Tool as ToolSchema,
    ToolSummary,
    ToolCategory as ToolCategorySchema,
    ToolListResponse,
    ToolDetailResponse,
    ToolExecutionResponse,
    ToolCreate,
    ToolUpdate
)


class ToolService:
    def __init__(self, db_session: AsyncSession):
        self.tool_repo = ToolRepository(db_session)
        self.category_repo = ToolCategoryRepository(db_session)
        self.usage_log_repo = ToolUsageLogRepository(db_session)

    async def get_all_tools(self) -> ToolListResponse:
        """获取所有工具列表"""
        tools = await self.tool_repo.get_all_tools()
        tool_summaries = [
            ToolSummary(
                id=tool.id,
                name=tool.name,
                description=tool.description,
                icon=tool.icon,
                category=tool.category,
                is_frontend=tool.is_frontend,
                is_backend=tool.is_backend
            )
            for tool in tools
        ]
        return ToolListResponse(tools=tool_summaries, total=len(tool_summaries))

    async def get_tools_by_category(self, category: str) -> ToolListResponse:
        """按分类获取工具"""
        tools = await self.tool_repo.get_tools_by_category(category)
        tool_summaries = [
            ToolSummary(
                id=tool.id,
                name=tool.name,
                description=tool.description,
                icon=tool.icon,
                category=tool.category,
                is_frontend=tool.is_frontend,
                is_backend=tool.is_backend
            )
            for tool in tools
        ]
        return ToolListResponse(tools=tool_summaries, total=len(tool_summaries))

    async def get_tool_detail(self, tool_id: UUID) -> Optional[ToolDetailResponse]:
        """获取工具详情"""
        tool = await self.tool_repo.get_tool_by_id(tool_id)
        if not tool:
            return None

        tool_schema = ToolSchema(
            id=tool.id,
            name=tool.name,
            description=tool.description,
            icon=tool.icon,
            category=tool.category,
            is_frontend=tool.is_frontend,
            is_backend=tool.is_backend,
            endpoint=tool.endpoint,
            parameters=tool.parameters,
            response_format=tool.response_format,
            enabled=tool.enabled,
            usage_count=tool.usage_count,
            created_at=tool.created_at,
            updated_at=tool.updated_at
        )

        related_tools = await self.tool_repo.get_tools_by_category(tool.category)
        related_summaries = [
            ToolSummary(
                id=t.id,
                name=t.name,
                description=t.description,
                icon=t.icon,
                category=t.category,
                is_frontend=t.is_frontend,
                is_backend=t.is_backend
            )
            for t in related_tools if t.id != tool_id
        ]

        return ToolDetailResponse(tool=tool_schema, related_tools=related_summaries[:5])

    async def search_tools(self, keyword: str) -> ToolListResponse:
        """搜索工具"""
        tools = await self.tool_repo.search_tools(keyword)
        tool_summaries = [
            ToolSummary(
                id=tool.id,
                name=tool.name,
                description=tool.description,
                icon=tool.icon,
                category=tool.category,
                is_frontend=tool.is_frontend,
                is_backend=tool.is_backend
            )
            for tool in tools
        ]
        return ToolListResponse(tools=tool_summaries, total=len(tool_summaries))

    async def get_frontend_tools(self) -> ToolListResponse:
        """获取前端工具列表"""
        tools = await self.tool_repo.get_frontend_tools()
        tool_summaries = [
            ToolSummary(
                id=tool.id,
                name=tool.name,
                description=tool.description,
                icon=tool.icon,
                category=tool.category,
                is_frontend=tool.is_frontend,
                is_backend=tool.is_backend
            )
            for tool in tools
        ]
        return ToolListResponse(tools=tool_summaries, total=len(tool_summaries))

    async def get_backend_tools(self) -> ToolListResponse:
        """获取后端工具列表"""
        tools = await self.tool_repo.get_backend_tools()
        tool_summaries = [
            ToolSummary(
                id=tool.id,
                name=tool.name,
                description=tool.description,
                icon=tool.icon,
                category=tool.category,
                is_frontend=tool.is_frontend,
                is_backend=tool.is_backend
            )
            for tool in tools
        ]
        return ToolListResponse(tools=tool_summaries, total=len(tool_summaries))

    async def get_categories(self) -> List[ToolCategorySchema]:
        """获取所有分类"""
        categories = await self.category_repo.get_category_with_tool_count()
        return [
            ToolCategorySchema(
                name=cat.name,
                display_name=cat.display_name,
                icon=cat.icon,
                description=cat.description,
                tool_count=cat.tool_count
            )
            for cat in categories
        ]

    async def execute_tool(
        self,
        tool_id: UUID,
        parameters: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> ToolExecutionResponse:
        """执行后端工具"""
        start_time = time.time()
        tool = await self.tool_repo.get_tool_by_id(tool_id)
        
        if not tool:
            return ToolExecutionResponse(
                success=False,
                message="Tool not found"
            )
        
        if not tool.is_backend:
            return ToolExecutionResponse(
                success=False,
                message="This tool is frontend-only"
            )
        
        if not tool.enabled:
            return ToolExecutionResponse(
                success=False,
                message="This tool is disabled"
            )
        
        try:
            result = await self._execute_backend_tool(tool.endpoint, parameters)
            execution_time = int((time.time() - start_time) * 1000)
            
            await self.tool_repo.increment_usage(tool_id)
            await self.usage_log_repo.create_log({
                "tool_id": tool_id,
                "user_id": user_id,
                "parameters": parameters,
                "result": result,
                "execution_time_ms": execution_time,
                "success": True
            })
            
            return ToolExecutionResponse(
                success=True,
                result=result,
                execution_time_ms=execution_time
            )
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            await self.usage_log_repo.create_log({
                "tool_id": tool_id,
                "user_id": user_id,
                "parameters": parameters,
                "result": None,
                "execution_time_ms": execution_time,
                "success": False,
                "error_message": str(e)
            })
            
            return ToolExecutionResponse(
                success=False,
                message=f"Tool execution failed: {str(e)}",
                execution_time_ms=execution_time
            )

    async def _execute_backend_tool(self, endpoint: str, parameters: Dict[str, Any]) -> Any:
        """调用后端工具接口"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, json=parameters, timeout=30.0)
            response.raise_for_status()
            return response.json()

    async def create_tool(self, tool_data: ToolCreate, user_id: Optional[UUID] = None) -> ToolSchema:
        """创建工具（管理员）"""
        tool = await self.tool_repo.create_tool(tool_data.model_dump())
        return ToolSchema(
            id=tool.id,
            name=tool.name,
            description=tool.description,
            icon=tool.icon,
            category=tool.category,
            is_frontend=tool.is_frontend,
            is_backend=tool.is_backend,
            endpoint=tool.endpoint,
            parameters=tool.parameters,
            response_format=tool.response_format,
            enabled=tool.enabled,
            usage_count=tool.usage_count,
            created_at=tool.created_at,
            updated_at=tool.updated_at
        )

    async def update_tool(self, tool_id: UUID, tool_data: ToolUpdate) -> Optional[ToolSchema]:
        """更新工具（管理员）"""
        update_data = {k: v for k, v in tool_data.model_dump().items() if v is not None}
        tool = await self.tool_repo.update_tool(tool_id, update_data)
        if not tool:
            return None
        
        return ToolSchema(
            id=tool.id,
            name=tool.name,
            description=tool.description,
            icon=tool.icon,
            category=tool.category,
            is_frontend=tool.is_frontend,
            is_backend=tool.is_backend,
            endpoint=tool.endpoint,
            parameters=tool.parameters,
            response_format=tool.response_format,
            enabled=tool.enabled,
            usage_count=tool.usage_count,
            created_at=tool.created_at,
            updated_at=tool.updated_at
        )