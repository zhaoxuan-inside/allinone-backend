from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import get_db
from stocks_service.schemas import (
    StockStrategy,
    TradeSignal,
    StrategyPerformance,
    StockInfo,
    KLineResponse,
    StrategyListResponse,
    TradeSignalListResponse
)
from stocks_service.service import StocksService

router = APIRouter(prefix="/stocks", tags=["stocks"])


def get_stocks_service(db: AsyncSession = Depends(get_db)) -> StocksService:
    return StocksService(db)


@router.get("/strategies", response_model=StrategyListResponse)
async def get_all_strategies(stocks_service: StocksService = Depends(get_stocks_service)):
    """获取所有股票策略列表"""
    return await stocks_service.get_all_strategies()


@router.get("/strategies/{strategy_id}", response_model=StockStrategy)
async def get_strategy_detail(
    strategy_id: UUID,
    stocks_service: StocksService = Depends(get_stocks_service)
):
    """获取策略详情"""
    strategy = await stocks_service.get_strategy_detail(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.get("/strategies/{strategy_id}/performance", response_model=StrategyPerformance)
async def get_strategy_performance(
    strategy_id: UUID,
    stocks_service: StocksService = Depends(get_stocks_service)
):
    """获取策略业绩"""
    performance = await stocks_service.get_strategy_performance(strategy_id)
    if not performance:
        raise HTTPException(status_code=404, detail="Performance not found")
    
    strategy = await stocks_service.get_strategy_detail(strategy_id)
    if strategy:
        performance.strategy_name = strategy.name
    
    return performance


@router.get("/strategies/{strategy_id}/signals", response_model=TradeSignalListResponse)
async def get_strategy_signals(
    strategy_id: UUID,
    stocks_service: StocksService = Depends(get_stocks_service)
):
    """获取策略的交易信号"""
    return await stocks_service.get_strategy_signals(strategy_id)


@router.get("/signals/today", response_model=TradeSignalListResponse)
async def get_today_signals(stocks_service: StocksService = Depends(get_stocks_service)):
    """获取今日交易信号"""
    return await stocks_service.get_today_signals()


@router.get("/kline/{stock_code}", response_model=KLineResponse)
async def get_stock_kline(
    stock_code: str,
    period: str = Query("day", enum=["day", "week", "month"]),
    days: int = Query(30, ge=1, le=365),
    stocks_service: StocksService = Depends(get_stocks_service)
):
    """获取股票K线数据"""
    kline = await stocks_service.get_kline(stock_code, period, days)
    if not kline:
        raise HTTPException(status_code=404, detail="Stock not found")
    return kline


@router.get("/info/{stock_code}", response_model=StockInfo)
async def get_stock_info(
    stock_code: str,
    stocks_service: StocksService = Depends(get_stocks_service)
):
    """获取股票基本信息"""
    stock_info = await stocks_service.get_stock_info(stock_code)
    if not stock_info:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock_info


@router.get("/search")
async def search_stocks(
    keyword: str,
    stocks_service: StocksService = Depends(get_stocks_service)
):
    """搜索股票"""
    if not keyword.strip():
        raise HTTPException(status_code=400, detail="Keyword is required")
    return await stocks_service.search_stocks(keyword)


@router.get("/list")
async def get_all_stocks(stocks_service: StocksService = Depends(get_stocks_service)):
    """获取所有股票列表"""
    return await stocks_service.get_all_stocks()