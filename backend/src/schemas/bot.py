from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List

# ===== API KEYS =====
class ApiKeyCreate(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(..., min_length=1)
    api_secret: str = Field(..., min_length=1)
    
    @validator('nickname')
    def validate_nickname(cls, v):
        if not v.strip():
            raise ValueError('Nickname не может быть пустым')
        return v.strip()


class ApiKeyResponse(BaseModel):
    id: int
    nickname: str
    exchange: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ===== BOT INDICATORS =====
class BotIndicatorCreate(BaseModel):
    type: str = Field(..., pattern="^(RSI|CCI)$")
    timeframe: str = Field(..., pattern="^(1m|5m|15m|1h|4h|1d)$")
    period: int = Field(..., ge=5, le=200)
    threshold: float
    direction: str = Field(..., pattern="^(above|below)$")
    
    @validator('threshold')
    def validate_threshold(cls, v, values):
        if 'type' in values:
            if values['type'] == 'RSI':
                if not (0 <= v <= 100):
                    raise ValueError('RSI threshold должен быть от 0 до 100')
            elif values['type'] == 'CCI':
                if not (-300 <= v <= 300):
                    raise ValueError('CCI threshold должен быть от -300 до 300')
        return v


class BotIndicatorResponse(BaseModel):
    id: int
    type: str
    timeframe: str
    period: int
    threshold: float
    direction: str
    
    class Config:
        from_attributes = True


# ===== BOTS =====
class BotCreate(BaseModel):
    api_key_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=100)
    trading_pair: str = Field(..., pattern="^[A-Z]+/[A-Z]+:[A-Z]+$")  # BTC/USDT:USDT
    strategy: str = Field(..., pattern="^(long|short)$")
    leverage: int = Field(10, ge=1, le=125)
    deposit: float = Field(..., gt=0, le=100000)
    take_profit_percent: float = Field(..., gt=0, le=100)
    stop_loss_percent: float = Field(..., gt=0, le=100)
    indicators: List[BotIndicatorCreate] = Field(..., min_items=1, max_items=5)
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Имя бота не может быть пустым')
        return v.strip()
    
    @validator('indicators')
    def validate_indicators(cls, v):
        if len(v) == 0:
            raise ValueError('Необходимо указать хотя бы один индикатор')
        return v


class BotResponse(BaseModel):
    id: int
    name: str
    trading_pair: str
    strategy: str
    leverage: int
    deposit: float
    take_profit_percent: float
    stop_loss_percent: float
    status: str
    container_id: Optional[str]
    created_at: datetime
    indicators: List[BotIndicatorResponse] = []
    
    class Config:
        from_attributes = True


class BotDetailResponse(BaseModel):
    id: int
    name: str
    trading_pair: str
    strategy: str
    leverage: int
    deposit: float
    take_profit_percent: float
    stop_loss_percent: float
    status: str
    container_id: Optional[str]
    created_at: datetime
    api_key: ApiKeyResponse
    indicators: List[BotIndicatorResponse]
    
    class Config:
        from_attributes = True
