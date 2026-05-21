from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from stocks_service.entities import StockStrategy, TradeSignal, StockKLine, StockInfo, StrategyPerformance
from stocks_service.repository import (
    StrategyRepository,
    TradeSignalRepository,
    StockKLineRepository,
    StockInfoRepository
)
from stocks_service.schemas import (
    StockStrategy as StockStrategySchema,
    TradeSignal as TradeSignalSchema,
    StrategyPerformance as StrategyPerformanceSchema,
    StockKLine as StockKLineSchema,
    StockInfo as StockInfoSchema,
    StrategyListResponse,
    TradeSignalListResponse,
    KLineResponse
)


class StocksService:
    def __init__(self, db_session: AsyncSession):
        self.strategy_repo = StrategyRepository(db_session)
        self.signal_repo = TradeSignalRepository(db_session)
        self.kline_repo = StockKLineRepository(db_session)
        self.stock_info_repo = StockInfoRepository(db_session)

    async def get_all_strategies(self) -> StrategyListResponse:
        """获取所有策略列表（包含业绩）"""
        strategies = await self.strategy_repo.get_all_strategies()
        
        strategy_schemas = []
        for strategy in strategies:
            performance = await self.strategy_repo.get_strategy_performance(strategy.id)
            
            strategy_schemas.append(StockStrategySchema(
                id=strategy.id,
                name=strategy.name,
                description=strategy.description,
                created_at=strategy.created_at,
                updated_at=strategy.updated_at,
                win_rate=performance.win_rate if performance else 0.0,
                total_profit=performance.total_profit if performance else 0.0,
                total_trades=performance.total_trades if performance else 0
            ))
        
        return StrategyListResponse(
            strategies=strategy_schemas,
            total=len(strategy_schemas)
        )

    async def get_strategy_detail(self, strategy_id: UUID) -> Optional[StockStrategySchema]:
        """获取策略详情"""
        strategy = await self.strategy_repo.get_strategy_by_id(strategy_id)
        if not strategy:
            return None
        
        performance = await self.strategy_repo.get_strategy_performance(strategy_id)
        
        return StockStrategySchema(
            id=strategy.id,
            name=strategy.name,
            description=strategy.description,
            created_at=strategy.created_at,
            updated_at=strategy.updated_at,
            win_rate=performance.win_rate if performance else 0.0,
            total_profit=performance.total_profit if performance else 0.0,
            total_trades=performance.total_trades if performance else 0
        )

    async def get_strategy_performance(self, strategy_id: UUID) -> Optional[StrategyPerformanceSchema]:
        """获取策略业绩"""
        performance = await self.strategy_repo.get_strategy_performance(strategy_id)
        if not performance:
            return None
        
        return StrategyPerformanceSchema(
            strategy_id=performance.strategy_id,
            strategy_name="",
            win_rate=performance.win_rate,
            total_profit=performance.total_profit,
            total_trades=performance.total_trades,
            win_trades=performance.win_trades,
            loss_trades=performance.loss_trades,
            avg_profit_per_trade=performance.avg_profit_per_trade,
            max_drawdown=performance.max_drawdown,
            start_date=performance.start_date,
            end_date=performance.end_date
        )

    async def get_strategy_signals(self, strategy_id: UUID) -> TradeSignalListResponse:
        """获取策略的交易信号"""
        today = datetime.now().date()
        today_start = datetime(today.year, today.month, today.day)
        
        signals = await self.signal_repo.get_signals_by_strategy(strategy_id, today_start)
        
        strategy = await self.strategy_repo.get_strategy_by_id(strategy_id)
        strategy_name = strategy.name if strategy else ""
        
        signal_schemas = [
            TradeSignalSchema(
                id=signal.id,
                strategy_id=signal.strategy_id,
                strategy_name=strategy_name,
                stock_code=signal.stock_code,
                stock_name=signal.stock_name,
                signal_type=signal.signal_type,
                buy_price=signal.buy_price,
                sell_price=signal.sell_price,
                target_price=signal.target_price,
                stop_loss_price=signal.stop_loss_price,
                signal_date=signal.signal_date,
                status=signal.status,
                actual_buy_price=signal.actual_buy_price,
                actual_sell_price=signal.actual_sell_price,
                profit=signal.profit,
                profit_rate=signal.profit_rate
            )
            for signal in signals
        ]
        
        return TradeSignalListResponse(
            signals=signal_schemas,
            total=len(signal_schemas)
        )

    async def get_today_signals(self) -> TradeSignalListResponse:
        """获取今日交易信号"""
        today = datetime.now().date()
        today_start = datetime(today.year, today.month, today.day)
        
        signals = await self.signal_repo.get_signals_by_date(today_start)
        
        signal_schemas = []
        for signal in signals:
            strategy = await self.strategy_repo.get_strategy_by_id(signal.strategy_id)
            strategy_name = strategy.name if strategy else ""
            
            signal_schemas.append(TradeSignalSchema(
                id=signal.id,
                strategy_id=signal.strategy_id,
                strategy_name=strategy_name,
                stock_code=signal.stock_code,
                stock_name=signal.stock_name,
                signal_type=signal.signal_type,
                buy_price=signal.buy_price,
                sell_price=signal.sell_price,
                target_price=signal.target_price,
                stop_loss_price=signal.stop_loss_price,
                signal_date=signal.signal_date,
                status=signal.status,
                actual_buy_price=signal.actual_buy_price,
                actual_sell_price=signal.actual_sell_price,
                profit=signal.profit,
                profit_rate=signal.profit_rate
            ))
        
        return TradeSignalListResponse(
            signals=signal_schemas,
            total=len(signal_schemas)
        )

    async def get_kline(
        self,
        stock_code: str,
        period: str = "day",
        days: int = 30
    ) -> Optional[KLineResponse]:
        """获取股票K线数据"""
        stock_info = await self.stock_info_repo.get_stock_info(stock_code)
        if not stock_info:
            return None
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        klines = await self.kline_repo.get_kline(stock_code, period, start_date, end_date)
        
        kline_schemas = [
            StockKLineSchema(
                stock_code=kline.stock_code,
                stock_name=kline.stock_name,
                date=kline.date,
                open=kline.open,
                close=kline.close,
                high=kline.high,
                low=kline.low,
                volume=kline.volume,
                turnover=kline.turnover
            )
            for kline in klines
        ]
        
        return KLineResponse(
            stock_code=stock_code,
            stock_name=stock_info.stock_name,
            period=period,
            data=kline_schemas
        )

    async def get_stock_info(self, stock_code: str) -> Optional[StockInfoSchema]:
        """获取股票基本信息"""
        stock_info = await self.stock_info_repo.get_stock_info(stock_code)
        if not stock_info:
            return None
        
        return StockInfoSchema(
            stock_code=stock_info.stock_code,
            stock_name=stock_info.stock_name,
            market=stock_info.market,
            industry=stock_info.industry,
            concept=stock_info.concept,
            pe=stock_info.pe,
            pb=stock_info.pb,
            eps=stock_info.eps
        )

    async def search_stocks(self, keyword: str) -> List[StockInfoSchema]:
        """搜索股票"""
        stocks = await self.stock_info_repo.search_stocks(keyword)
        return [
            StockInfoSchema(
                stock_code=stock.stock_code,
                stock_name=stock.stock_name,
                market=stock.market,
                industry=stock.industry,
                concept=stock.concept,
                pe=stock.pe,
                pb=stock.pb,
                eps=stock.eps
            )
            for stock in stocks
        ]

    async def get_all_stocks(self) -> List[StockInfoSchema]:
        """获取所有股票列表"""
        stocks = await self.stock_info_repo.get_all_stocks()
        return [
            StockInfoSchema(
                stock_code=stock.stock_code,
                stock_name=stock.stock_name,
                market=stock.market,
                industry=stock.industry,
                concept=stock.concept,
                pe=stock.pe,
                pb=stock.pb,
                eps=stock.eps
            )
            for stock in stocks
        ]