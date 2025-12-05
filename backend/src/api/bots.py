"""
Добавить в существующий файл backend/src/api/bots.py
"""

# Добавить импорты в начало файла:
from ..services.docker_manager import DockerManager
import logging

logger = logging.getLogger(__name__)

# Создать экземпляр Docker Manager после создания router:
docker_manager = DockerManager()


# ========== НОВЫЕ ЭНДПОИНТЫ ==========

@router.post("/{bot_id}/start", response_model=ApiResponse)
async def start_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Запустить бота в Docker контейнере
    
    Действия:
    1. Проверка прав доступа
    2. Получение и расшифровка API ключей
    3. Сборка конфигурации с индикаторами
    4. Запуск контейнера через Docker Manager
    5. Обновление статуса в БД
    """
    try:
        # Получить бота и проверить владельца
        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            return ApiResponse(
                success=False,
                error="Бот не найден или у вас нет прав доступа"
            )
        
        # Проверка что бот не запущен
        if bot.status == "running":
            return ApiResponse(
                success=False,
                error="Бот уже запущен"
            )
        
        # Получить API ключ и расшифровать
        api_key_obj = db.query(ApiKey).filter(
            ApiKey.id == bot.api_key_id,
            ApiKey.user_id == current_user.id
        ).first()
        
        if not api_key_obj:
            return ApiResponse(
                success=False,
                error="API ключ не найден"
            )
        
        # Расшифровка ключей
        try:
            decrypted_key = decrypt_api_key(api_key_obj.api_key)
            decrypted_secret = decrypt_api_key(api_key_obj.api_secret)
        except Exception as e:
            logger.error(f"Ошибка расшифровки API ключей: {e}")
            return ApiResponse(
                success=False,
                error="Ошибка расшифровки API ключей"
            )
        
        # Получить все индикаторы бота
        indicators = db.query(BotIndicator).filter(
            BotIndicator.bot_id == bot_id
        ).all()
        
        indicators_list = [
            {
                "type": ind.indicator_type,
                "period": ind.period,
                "value": ind.value,
                "condition": ind.condition
            }
            for ind in indicators
        ]
        
        # Собрать конфигурацию бота
        bot_config = {
            "trading_pair": bot.trading_pair,
            "strategy": bot.strategy,
            "leverage": bot.leverage,
            "deposit": float(bot.deposit),
            "take_profit_percent": float(bot.take_profit_percent),
            "stop_loss_percent": float(bot.stop_loss_percent),
            "indicators": indicators_list,
            "exchange": api_key_obj.exchange
        }
        
        # Запустить контейнер через Docker Manager
        container_id, error = docker_manager.start_bot_container(
            bot_id=bot_id,
            bot_config=bot_config,
            api_key=decrypted_key,
            api_secret=decrypted_secret
        )
        
        if error:
            logger.error(f"Ошибка запуска контейнера для бота {bot_id}: {error}")
            return ApiResponse(
                success=False,
                error=f"Ошибка запуска контейнера: {error}"
            )
        
        # Обновить статус и container_id в БД
        bot.status = "running"
        bot.container_id = container_id
        db.commit()
        
        logger.info(f"Бот {bot_id} успешно запущен. Container ID: {container_id}")
        
        return ApiResponse(
            success=True,
            data={
                "bot_id": bot_id,
                "container_id": container_id,
                "status": "running"
            }
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Неожиданная ошибка при запуске бота {bot_id}: {e}")
        return ApiResponse(
            success=False,
            error=f"Внутренняя ошибка сервера: {str(e)}"
        )


@router.post("/{bot_id}/stop", response_model=ApiResponse)
async def stop_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Остановить Docker контейнер бота
    
    Действия:
    1. Проверка прав и статуса
    2. Остановка и удаление контейнера
    3. Обновление статуса в БД
    """
    try:
        # Получить бота и проверить владельца
        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            return ApiResponse(
                success=False,
                error="Бот не найден или у вас нет прав доступа"
            )
        
        # Проверка что бот запущен
        if bot.status != "running":
            return ApiResponse(
                success=False,
                error="Бот не запущен"
            )
        
        if not bot.container_id:
            return ApiResponse(
                success=False,
                error="У бота отсутствует ID контейнера"
            )
        
        # Остановить контейнер через Docker Manager
        success = docker_manager.stop_bot_container(bot.container_id)
        
        if not success:
            logger.error(f"Не удалось остановить контейнер {bot.container_id}")
            return ApiResponse(
                success=False,
                error="Ошибка остановки контейнера. Попробуйте позже."
            )
        
        # Обновить статус в БД
        bot.status = "stopped"
        bot.container_id = None
        db.commit()
        
        logger.info(f"Бот {bot_id} успешно остановлен")
        
        return ApiResponse(
            success=True,
            data={
                "bot_id": bot_id,
                "status": "stopped"
            }
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Неожиданная ошибка при остановке бота {bot_id}: {e}")
        return ApiResponse(
            success=False,
            error=f"Внутренняя ошибка сервера: {str(e)}"
        )


@router.get("/{bot_id}/logs", response_model=ApiResponse)
async def get_bot_logs(
    bot_id: int,
    tail: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить логи контейнера бота
    
    Query параметры:
    - tail: количество последних строк (по умолчанию 50, макс 500)
    """
    try:
        # Ограничение максимального количества строк
        if tail > 500:
            tail = 500
        
        # Получить бота и проверить владельца
        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot:
            return ApiResponse(
                success=False,
                error="Бот не найден или у вас нет прав доступа"
            )
        
        # Проверка наличия container_id
        if not bot.container_id:
            return ApiResponse(
                success=False,
                error="Бот не запущен или контейнер был удален"
            )
        
        # Получить логи через Docker Manager
        logs = docker_manager.get_container_logs(bot.container_id, tail=tail)
        
        if logs is None:
            return ApiResponse(
                success=False,
                error="Контейнер не найден. Возможно бот был остановлен."
            )
        
        # Проверка актуального статуса контейнера
        is_running = docker_manager.is_container_running(bot.container_id)
        
        # Синхронизация статуса если контейнер не запущен
        if not is_running and bot.status == "running":
            bot.status = "stopped"
            bot.container_id = None
            db.commit()
            logger.warning(f"Бот {bot_id} был помечен как running, но контейнер не найден. Статус обновлен.")
        
        return ApiResponse(
            success=True,
            data={
                "bot_id": bot_id,
                "logs": logs,
                "lines_count": len(logs.split('\n')) if logs else 0,
                "is_running": is_running
            }
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении логов бота {bot_id}: {e}")
        return ApiResponse(
            success=False,
            error=f"Внутренняя ошибка сервера: {str(e)}"
        )


# Опционально: эндпоинт для получения статистики ресурсов
@router.get("/{bot_id}/stats", response_model=ApiResponse)
async def get_bot_stats(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статистику использования ресурсов контейнера"""
    try:
        bot = db.query(Bot).filter(
            Bot.id == bot_id,
            Bot.user_id == current_user.id
        ).first()
        
        if not bot or not bot.container_id:
            return ApiResponse(
                success=False,
                error="Бот не найден или не запущен"
            )
        
        stats = docker_manager.get_container_stats(bot.container_id)
        
        if not stats:
            return ApiResponse(
                success=False,
                error="Не удалось получить статистику"
            )
        
        return ApiResponse(
            success=True,
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return ApiResponse(
            success=False,
            error=str(e)
        )
