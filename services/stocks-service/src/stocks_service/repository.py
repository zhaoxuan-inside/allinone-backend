from typing import Optional, List
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, update, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.stocks_service.entities import StockStrategy, TradeSignal, StockKLine, StockInfo, StrategyPerformance


class StrategyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_strategies(self) -> List[StockStrategy]:
        result = await self.session.execute(select(StockStrategy).where(StockStrategy.enabled == True))
        return list(result.scalars().all())

    async def get_strategy_by_id(self, strategy_id: UUID) -> Optional[StockStrategy]:
        result = await self.session.execute(select(StockStrategy).where(StockStrategy.id == strategy_id))
        return result.scalar_one_or_none()

    async def get_strategy_performance(self, strategy_id: UUID) -> Optional[StrategyPerformance]:
        result = await self.session.execute(select(StrategyPerformance).where(StrategyPerformance.strategy_id == strategy_id))
        return result.scalar_one_or_none()


class TradeSignalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_signals_by_strategy(self, strategy_id: UUID, date: Optional[datetime] = None) -> List[TradeSignal]:
        query = select(TradeSignal).where(TradeSignal.strategy_id == strategy_id)
        
        if date:
            query = query.where(TradeSignal.signal_date >= date)
        
        query = query.order_by(desc(TradeSignal.signal_date))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_signals_by_date(self, date: datetime) -> List[TradeSignal]:
        result = await self.session.execute(
            select(TradeSignal)
            .where(TradeSignal.signal_date >= date)
            .order_by(desc(TradeSignal.signal_date))
        )
        return list(result.scalars().all())

    async def get_signals_by_stock(self, stock_code: str) -> List[TradeSignal]:
        result = await self.session.execute(
            select(TradeSignal)
            .where(TradeSignal.stock_code == stock_code)
            .order_by(desc(TradeSignal.signal_date))
        )
        return list(result.scalars().all())

    async def get_signal_by_id(self, signal_id: UUID) -> Optional[TradeSignal]:
        result = await self.session.execute(select(TradeSignal).where(TradeSignal.id == signal_id))
        return result.scalar_one_or_none()


class StockKLineRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_kline(
        self,
        stock_code: str,
        period: str = "day",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[StockKLine]:
        query = select(StockKLine).where(
            StockKLine.stock_code == stock_code,
            StockKLine.period == period
        )
        
        if start_date:
            query = query.where(StockKLine.date >= start_date)
        if end_date:
            query = query.where(StockKLine.date <= end_date)
        
        query = query.order_by(StockKLine.date)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class StockInfoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_stock_info(self, stock_code: str) -> Optional[StockInfo]:
        result = await self.session.execute(select(StockInfo).where(StockInfo.stock_code == stock_code))
        return result.scalar_one_or_none()

    async def search_stocks(self, keyword: str) -> List[StockInfo]:
        result = await self.session.execute(
            select(StockInfo)
            .where(
                StockInfo.stock_code.ilike(f"%{keyword}%") | 
                StockInfo.stock_name.ilike(f"%{keyword}%")
            )
            .order_by(StockInfo.stock_code)
        )
        return list(result.scalars().all())

    async def get_all_stocks(self) -> List[StockInfo]:
        result = await self.session.execute(select(StockInfo).order_by(StockInfo.stock_code))
        return list(result.scalars().all())