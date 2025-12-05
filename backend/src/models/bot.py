from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class Bot(Base):
    """
    Модель торгового бота.
    Хранит конфигурацию бота и связан с Docker контейнером.
    """
    __tablename__ = "bots"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    trading_pair = Column(String(50), nullable=False)  # Например: BTC/USDT:USDT
    strategy = Column(String(10), nullable=False)  # "long" или "short"
    leverage = Column(Integer, default=10, nullable=False)
    deposit = Column(Numeric(10, 2), nullable=False)  # Депозит в USDT
    
    take_profit_percent = Column(Numeric(5, 2), nullable=False)
    stop_loss_percent = Column(Numeric(5, 2), nullable=True)  # Опционально
    
    status = Column(String(20), default="stopped", nullable=False)  # "running", "stopped"
    container_id = Column(String(100), nullable=True)  # Docker container ID
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="bots")
    api_key = relationship("ApiKey", back_populates="bots")
    indicators = relationship(
        "BotIndicator",
        back_populates="bot",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    def __repr__(self):
        return f"<Bot(id={self.id}, name='{self.name}', pair='{self.trading_pair}', status='{self.status}')>"


class BotIndicator(Base):
    """
    Модель технических индикаторов для бота.
    Определяет условия входа в позицию (RSI, CCI и т.д.).
    """
    __tablename__ = "bot_indicators"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    
    indicator_type = Column(String(20), nullable=False)  # "RSI", "CCI", "EMA"
    timeframe = Column(String(10), nullable=False)  # "1m", "5m", "15m", "1h", "4h", "1d"
    period = Column(Integer, nullable=False)  # Период индикатора
    threshold = Column(Numeric(10, 2), nullable=False)  # Пороговое значение
    direction = Column(String(10), nullable=False)  # "above", "below"
    
    # Relationships
    bot = relationship("Bot", back_populates="indicators")
    
    def __repr__(self):
        return f"<BotIndicator(id={self.id}, bot_id={self.bot_id}, type='{self.indicator_type}', timeframe='{self.timeframe}')>"
