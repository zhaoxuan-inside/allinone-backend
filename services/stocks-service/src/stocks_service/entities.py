from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text, Float, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from common.database import Base


class StockStrategy(Base):
    __tablename__ = "strategies"
    __table_args__ = {"schema": "stocks"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    enabled = Column(Boolean, default=True)


class TradeSignal(Base):
    __tablename__ = "trade_signals"
    __table_args__ = {"schema": "stocks"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    strategy_id = Column(UUID(as_uuid=True), nullable=False)
    stock_code = Column(String(20), nullable=False)
    stock_name = Column(String(100), nullable=False)
    signal_type = Column(String(20), nullable=False)  # buy, sell, hold
    buy_price = Column(Float)
    sell_price = Column(Float)
    target_price = Column(Float)
    stop_loss_price = Column(Float)
    signal_date = Column(DateTime, nullable=False)
    status = Column(String(20), default="pending")  # pending, executed, closed
    actual_buy_price = Column(Float)
    actual_sell_price = Column(Float)
    profit = Column(Float)
    profit_rate = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StockKLine(Base):
    __tablename__ = "stock_kline"
    __table_args__ = {"schema": "stocks"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    stock_code = Column(String(20), nullable=False)
    stock_name = Column(String(100), nullable=False)
    period = Column(String(20), nullable=False)  # day, week, month
    date = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    volume = Column(Integer)
    turnover = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class StockInfo(Base):
    __tablename__ = "stock_info"
    __table_args__ = {"schema": "stocks"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    stock_code = Column(String(20), unique=True, nullable=False)
    stock_name = Column(String(100), nullable=False)
    market = Column(String(10))  # sh, sz
    industry = Column(String(100))
    concept = Column(String(200))
    pe = Column(Float)
    pb = Column(Float)
    eps = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StrategyPerformance(Base):
    __tablename__ = "strategy_performance"
    __table_args__ = {"schema": "stocks"}

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    strategy_id = Column(UUID(as_uuid=True), unique=True, nullable=False)
    win_rate = Column(Float, default=0.0)
    total_profit = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    win_trades = Column(Integer, default=0)
    loss_trades = Column(Integer, default=0)
    avg_profit_per_trade = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow)