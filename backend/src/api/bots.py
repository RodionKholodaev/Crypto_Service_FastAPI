from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import logging

from ..core.database import get_db
from ..core.security import encrypt_api_key, decrypt_api_key
from ..models.user import User
from ..models.api_key import ApiKey
from ..models.bot import Bot, BotIndicator
from ..schemas.bot import (
    ApiKeyCreate, ApiKeyResponse,
    BotCreate, BotResponse, BotDetailResponse,
    BotIndicatorCreate
)
from ..schemas.auth import ApiResponse
from ..services.exchange_api import ExchangeAPI

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["bots"])


# ===== DEPENDENCY =====
def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Получить текущего пользователя из заголовка Authorization
    
    Args:
        authorization: Bearer токен с user_id
        db: Сессия базы данных
        
    Returns:
        Объект User
        
    Raises:
        HTTPException: Если пользователь не авторизован или не найден
    """
    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("Отсутствует или неверный заголовок Authorization")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация"
        )
    
    try:
        user_id = int(authorization.replace("Bearer ", ""))
    except ValueError:
        logger.warning(f"Неверный формат user_id в токене: {authorization}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен авторизации"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"Пользователь с id={user_id} не найден")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден"
        )
    
    logger.info(f"Пользователь {user.username} (id={user.id}) авторизован")
    return user


# ===== API KEYS =====
@router.post("/api-keys", response_model=ApiResponse)
async def create_api_key(
    key_data: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Создать новый API ключ для биржи
    
    Проверяет работоспособность ключей через биржу,
    шифрует их и сохраняет в базу данных
    """
    logger.info(f"Создание API ключа '{key_data.nickname}' для пользователя {current_user.username}")
    
    try:
        # 1. Проверяем что API ключ работает
        exchange_api = ExchangeAPI(
            api_key=key_data.api_key,
            api_secret=key_data.api_secret,
            exchange_name="bybit"
        )
        
        if not exchange_api.test_connection():
            logger.warning(f"API ключ '{key_data.nickname}' не прошел проверку")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверные API ключи или нет доступа к API биржи"
            )
        
        # 2. Шифруем ключи
        encrypted_key = encrypt_api_key(key_data.api_key)
        encrypted_secret = encrypt_api_key(key_data.api_secret)
        
        # 3. Создаем запись в БД
        api_key = ApiKey(
            user_id=current_user.id,
            nickname=key_data.nickname,
            api_key=encrypted_key,
            api_secret=encrypted_secret,
            exchange="bybit"
        )
        
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        
        logger.info(f"API ключ '{key_data.nickname}' (id={api_key.id}) успешно создан")
        
        return ApiResponse(
            success=True,
            data={"id": api_key.id, "nickname": api_key.nickname},
            message="API ключ успешно добавлен"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании API ключа: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании API ключа: {str(e)}"
        )


@router.get("/api-keys", response_model=ApiResponse)
async def get_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить все API ключи текущего пользователя
    """
    logger.info(f"Получение API ключей для пользователя {current_user.username}")
    
    api_keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()
    
    keys_response = [
        ApiKeyResponse(
            id=key.id,
            nickname=key.nickname,
            exchange=key.exchange,
            created_at=key.created_at
        )
        for key in api_keys
    ]
    
    logger.info(f"Найдено {len(keys_response)} API ключей")
    
    return ApiResponse(
        success=True,
        data=keys_response,
        message=f"Найдено {len(keys_response)} API ключей"
    )


@router.delete("/api-keys/{key_id}", response_model=ApiResponse)
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Удалить API ключ
    
    Проверяет что ключ принадлежит пользователю
    и что нет активных ботов использующих этот ключ
    """
    logger.info(f"Удаление API ключа id={key_id} для пользователя {current_user.username}")
    
    # 1. Проверяем что ключ принадлежит пользователю
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        logger.warning(f"API ключ id={key_id} не найден или не принадлежит пользователю")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API ключ не найден"
        )
    
    # 2. Проверяем что нет активных ботов
    active_bots = db.query(Bot).filter(
        Bot.api_key_id == key_id,
        Bot.status == "running"
    ).count()
    
    if active_bots > 0:
        logger.warning(f"Попытка удалить API ключ id={key_id} с {active_bots} активными ботами")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Нельзя удалить API ключ, используется в {active_bots} активных ботах"
        )
    
    # 3. Удаляем ключ
    try:
        db.delete(api_key)
        db.commit()
        logger.info(f"API ключ id={key_id} успешно удален")
        
        return ApiResponse(
            success=True,
            data={"id": key_id},
            message="API ключ успешно удален"
        )
    except Exception as e:
        logger.error(f"Ошибка при удалении API ключа: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении API ключа: {str(e)}"
        )


# ===== BOTS =====
@router.post("/bots", response_model=ApiResponse)
async def create_bot(
    bot_data: BotCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Создать нового торгового бота
    
    Проверяет что API ключ принадлежит пользователю,
    создает бота и все его индикаторы
    """
    logger.info(f"Создание бота '{bot_data.name}' для пользователя {current_user.username}")
    
    # 1. Проверяем что api_key принадлежит пользователю
    api_key = db.query(ApiKey).filter(
        ApiKey.id == bot_data.api_key_id,
        ApiKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        logger.warning(f"API ключ id={bot_data.api_key_id} не найден или не принадлежит пользователю")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API ключ не найден"
        )
    
    try:
        # 2. Создаем бота
        bot = Bot(
            user_id=current_user.id,
            api_key_id=bot_data.api_key_id,
            name=bot_data.name,
            trading_pair=bot_data.trading_pair,
            strategy=bot_data.strategy,
            leverage=bot_data.leverage,
            deposit=bot_data.deposit,
            take_profit_percent=bot_data.take_profit_percent,
            stop_loss_percent=bot_data.stop_loss_percent,
            status="stopped",
            container_id=None
        )
        
        db.add(bot)
        db.flush()  # Получаем bot.id
        
        # 3. Создаем индикаторы
        for indicator_data in bot_data.indicators:
            indicator = BotIndicator(
                bot_id=bot.id,
                type=indicator_data.type,
                timeframe=indicator_data.timeframe,
                period=indicator_data.period,
                threshold=indicator_data.threshold,
                direction=indicator_data.direction
            )
            db.add(indicator)
        
        db.commit()
        db.refresh(bot)
        
        logger.info(f"Бот '{bot_data.name}' (id={bot.id}) успешно создан с {len(bot_data.indicators)} индикаторами")
        
        return ApiResponse(
            success=True,
            data={"bot_id": bot.id, "name": bot.name},
            message="Бот успешно создан"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при создании бота: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании бота: {str(e)}"
        )


@router.get("/bots", response_model=ApiResponse)
async def get_bots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить все боты текущего пользователя с индикаторами
    """
    logger.info(f"Получение ботов для пользователя {current_user.username}")
    
    bots = db.query(Bot).filter(
        Bot.user_id == current_user.id
    ).options(joinedload(Bot.indicators)).all()
    
    bots_response = [
        BotResponse(
            id=bot.id,
            name=bot.name,
            trading_pair=bot.trading_pair,
            strategy=bot.strategy,
            leverage=bot.leverage,
            deposit=bot.deposit,
            take_profit_percent=bot.take_profit_percent,
            stop_loss_percent=bot.stop_loss_percent,
            status=bot.status,
            container_id=bot.container_id,
            created_at=bot.created_at,
            indicators=[
                {
                    "id": ind.id,
                    "type": ind.type,
                    "timeframe": ind.timeframe,
                    "period": ind.period,
                    "threshold": ind.threshold,
                    "direction": ind.direction
                }
                for ind in bot.indicators
            ]
        )
        for bot in bots
    ]
    
    logger.info(f"Найдено {len(bots_response)} ботов")
    
    return ApiResponse(
        success=True,
        data=bots_response,
        message=f"Найдено {len(bots_response)} ботов"
    )


@router.get("/bots/{bot_id}", response_model=ApiResponse)
async def get_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить детальную информацию о боте включая индикаторы и API ключ
    """
    logger.info(f"Получение бота id={bot_id} для пользователя {current_user.username}")
    
    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        Bot.user_id == current_user.id
    ).options(
        joinedload(Bot.indicators),
        joinedload(Bot.api_key)
    ).first()
    
    if not bot:
        logger.warning(f"Бот id={bot_id} не найден или не принадлежит пользователю")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бот не найден"
        )
    
    bot_response = BotDetailResponse(
        id=bot.id,
        name=bot.name,
        trading_pair=bot.trading_pair,
        strategy=bot.strategy,
        leverage=bot.leverage,
        deposit=bot.deposit,
        take_profit_percent=bot.take_profit_percent,
        stop_loss_percent=bot.stop_loss_percent,
        status=bot.status,
        container_id=bot.container_id,
        created_at=bot.created_at,
        api_key=ApiKeyResponse(
            id=bot.api_key.id,
            nickname=bot.api_key.nickname,
            exchange=bot.api_key.exchange,
            created_at=bot.api_key.created_at
        ),
        indicators=[
            {
                "id": ind.id,
                "type": ind.type,
                "timeframe": ind.timeframe,
                "period": ind.period,
                "threshold": ind.threshold,
                "direction": ind.direction
            }
            for ind in bot.indicators
        ]
    )
    
    logger.info(f"Бот id={bot_id} успешно получен")
    
    return ApiResponse(
        success=True,
        data=bot_response,
        message="Бот найден"
    )


@router.delete("/bots/{bot_id}", response_model=ApiResponse)
async def delete_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Удалить бота
    
    Проверяет что бот принадлежит пользователю
    и что бот остановлен
    """
    logger.info(f"Удаление бота id={bot_id} для пользователя {current_user.username}")
    
    # 1. Проверяем что бот принадлежит пользователю
    bot = db.query(Bot).filter(
        Bot.id == bot_id,
        Bot.user_id == current_user.id
    ).first()
    
    if not bot:
        logger.warning(f"Бот id={bot_id} не найден или не принадлежит пользователю")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Бот не найден"
        )
    
    # 2. Проверяем что бот остановлен
    if bot.status == "running":
        logger.warning(f"Попытка удалить запущенного бота id={bot_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сначала остановите бота"
        )
    
    # 3. Удаляем бота (cascade удалит indicators)
    try:
        db.delete(bot)
        db.commit()
        logger.info(f"Бот id={bot_id} успешно удален")
        
        return ApiResponse(
            success=True,
            data={"id": bot_id},
            message="Бот успешно удален"
        )
    except Exception as e:
        logger.error(f"Ошибка при удалении бота: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении бота: {str(e)}"
        )
