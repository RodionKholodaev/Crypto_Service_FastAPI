from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base


class ApiKey(Base):
    """
    Модель API ключей биржи.
    Ключи хранятся в зашифрованном виде (Fernet encryption).
    """
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exchange_name = Column(String(50), default="Bybit", nullable=False)
    nickname = Column(String(100), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)  # Зашифрованный API ключ
    api_secret_encrypted = Column(Text, nullable=False)  # Зашифрованный API secret
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    bots = relationship(
        "Bot",
        back_populates="api_key",
        lazy="select"
    )
    
    def __repr__(self):
        return f"<ApiKey(id={self.id}, user_id={self.user_id}, exchange='{self.exchange_name}', nickname='{self.nickname}')>"
