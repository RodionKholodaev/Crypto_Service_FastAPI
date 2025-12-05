from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# Создание engine для подключения к PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    echo=True,  # Логирование SQL запросов (отключить в production)
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_size=10,  # Размер пула соединений
    max_overflow=20  # Максимальное количество дополнительных соединений
)

# Фабрика сессий для работы с БД
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Базовый класс для всех моделей
Base = declarative_base()


# Dependency для FastAPI endpoints
def get_db():
    """
    Генератор сессии БД для использования в FastAPI через Depends().
    Автоматически закрывает сессию после завершения запроса.
    
    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
