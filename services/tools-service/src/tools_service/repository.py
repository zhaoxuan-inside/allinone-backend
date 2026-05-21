from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from tools_service.entities import Tool, ToolCategory, ToolUsageLog


class ToolRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_tools(self, enabled_only: bool = True) -> List[Tool]:
        query = select(Tool)
        if enabled_only:
            query = query.where(Tool.enabled == True)
        query = query.order_by(Tool.category, Tool.name)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_tools_by_category(self, category: str, enabled_only: bool = True) -> List[Tool]:
        query = select(Tool).where(Tool.category == category)
        if enabled_only:
            query = query.where(Tool.enabled == True)
        query = query.order_by(Tool.name)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_tool_by_id(self, tool_id: UUID) -> Optional[Tool]:
        result = await self.session.execute(select(Tool).where(Tool.id == tool_id))
        return result.scalar_one_or_none()

    async def get_tool_by_name(self, name: str) -> Optional[Tool]:
        result = await self.session.execute(select(Tool).where(Tool.name == name))
        return result.scalar_one_or_none()

    async def create_tool(self, tool_data: dict) -> Tool:
        tool = Tool(**tool_data)
        self.session.add(tool)
        await self.session.commit()
        await self.session.refresh(tool)
        return tool

    async def update_tool(self, tool_id: UUID, tool_data: dict) -> Optional[Tool]:
        await self.session.execute(
            update(Tool).where(Tool.id == tool_id).values(**tool_data)
        )
        await self.session.commit()
        return await self.get_tool_by_id(tool_id)

    async def increment_usage(self, tool_id: UUID) -> None:
        await self.session.execute(
            update(Tool).where(Tool.id == tool_id).values(
                usage_count=Tool.usage_count + 1
            )
        )
        await self.session.commit()

    async def search_tools(self, keyword: str, enabled_only: bool = True) -> List[Tool]:
        query = select(Tool).where(
            Tool.name.ilike(f"%{keyword}%") | Tool.description.ilike(f"%{keyword}%")
        )
        if enabled_only:
            query = query.where(Tool.enabled == True)
        query = query.order_by(Tool.name)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_frontend_tools(self, enabled_only: bool = True) -> List[Tool]:
        query = select(Tool).where(Tool.is_frontend == True)
        if enabled_only:
            query = query.where(Tool.enabled == True)
        query = query.order_by(Tool.category, Tool.name)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_backend_tools(self, enabled_only: bool = True) -> List[Tool]:
        query = select(Tool).where(Tool.is_backend == True)
        if enabled_only:
            query = query.where(Tool.enabled == True)
        query = query.order_by(Tool.category, Tool.name)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class ToolCategoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_categories(self) -> List[ToolCategory]:
        result = await self.session.execute(
            select(ToolCategory).order_by(ToolCategory.sort_order, ToolCategory.display_name)
        )
        return list(result.scalars().all())

    async def get_category_by_name(self, name: str) -> Optional[ToolCategory]:
        result = await self.session.execute(
            select(ToolCategory).where(ToolCategory.name == name)
        )
        return result.scalar_one_or_none()

    async def create_category(self, category_data: dict) -> ToolCategory:
        category = ToolCategory(**category_data)
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def get_category_with_tool_count(self) -> List[dict]:
        result = await self.session.execute(
            select(
                ToolCategory.name,
                ToolCategory.display_name,
                ToolCategory.icon,
                ToolCategory.description,
                func.count(Tool.id).label("tool_count")
            )
            .outerjoin(Tool, ToolCategory.name == Tool.category)
            .where(Tool.enabled == True)
            .group_by(ToolCategory.id, ToolCategory.name, ToolCategory.display_name, ToolCategory.icon, ToolCategory.description)
            .order_by(ToolCategory.sort_order, ToolCategory.display_name)
        )
        return list(result.all())


class ToolUsageLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_log(self, log_data: dict) -> ToolUsageLog:
        log = ToolUsageLog(**log_data)
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log