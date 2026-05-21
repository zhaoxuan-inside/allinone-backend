from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel


class StockStrategy(BaseModel):
    """股票策略信息"""
    id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    win_rate: float
    total_profit: float
    total_trades: int


class TradeSignal(BaseModel):
    """交易信号"""
    id: UUID
    strategy_id: UUID
    strategy_name: str
    stock_code: str
    stock_name: str
    signal_type: str  # buy, sell, hold
    buy_price: Optional[float]
    sell_price: Optional[float]
    target_price: Optional[float]
    stop_loss_price: Optional[float]
    signal_date: datetime
    status: str  # pending, executed, closed
    actual_buy_price: Optional[float]
    actual_sell_price: Optional[float]
    profit: Optional[float]
    profit_rate: Optional[float]


class StrategyPerformance(BaseModel):
    """策略业绩"""
    strategy_id: UUID
    strategy_name: str
    win_rate: float
    total_profit: float
    total_trades: int
    win_trades: int
    loss_trades: int
    avg_profit_per_trade: float
    max_drawdown: float
    start_date: datetime
    end_date: datetime


class StockKLine(BaseModel):
    """K线数据"""
    stock_code: str
    stock_name: str
    date: datetime
    open: float
    close: float
    high: float
    low: float
    volume: int
    turnover: float


class StockInfo(BaseModel):
    """股票基本信息"""
    stock_code: str
    stock_name: str
    market: str  # sh, sz
    industry: Optional[str]
    concept: Optional[str]
    pe: Optional[float]
    pb: Optional[float]
    eps: Optional[float]


class StockSearchRequest(BaseModel):
    """股票搜索请求"""
    keyword: str


class StrategyListResponse(BaseModel):
    """策略列表响应"""
    strategies: List[StockStrategy]
    total: int


class TradeSignalListResponse(BaseModel):
    """交易信号列表响应"""
    signals: List[TradeSignal]
    total: int


class KLineResponse(BaseModel):
    """K线响应"""
    stock_code: str
    stock_name: str
    period: str  # day, week, month
    data: List[StockKLine]