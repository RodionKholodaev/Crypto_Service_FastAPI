"""
Docker Manager для управления контейнерами торговых ботов
"""
import docker
import json
import logging
from typing import Optional, Tuple
from docker.errors import ImageNotFound, NotFound, APIError

logger = logging.getLogger(__name__)


class DockerManager:
    """Менеджер для управления Docker контейнерами ботов"""
    
    def __init__(self):
        """Подключение к Docker daemon через /var/run/docker.sock"""
        try:
            self.client = docker.from_env()
            # Проверка подключения
            self.client.ping()
            logger.info("Docker Manager успешно подключен к Docker daemon")
        except Exception as e:
            logger.error(f"Ошибка подключения к Docker: {e}")
            raise
    
    def start_bot_container(
        self,
        bot_id: int,
        bot_config: dict,
        api_key: str,
        api_secret: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Запустить бота в отдельном Docker контейнере
        
        Args:
            bot_id: ID бота в базе данных
            bot_config: Конфигурация бота (пара, стратегия, leverage, депозит, TP/SL, индикаторы)
            api_key: Расшифрованный API ключ биржи
            api_secret: Расшифрованный API secret биржи
            
        Returns:
            (container_id, error): ID контейнера или None с сообщением об ошибке
        """
        container_name = f"trading-bot-{bot_id}"
        
        try:
            # Проверка существования образа
            try:
                self.client.images.get("bot-runner:latest")
            except ImageNotFound:
                error_msg = "Образ bot-runner:latest не найден. Необходимо собрать образ."
                logger.error(error_msg)
                return None, error_msg
            
            # Удаление старого контейнера с таким же именем (если существует)
            try:
                old_container = self.client.containers.get(container_name)
                logger.info(f"Найден старый контейнер {container_name}, удаляю...")
                old_container.stop(timeout=5)
                old_container.remove()
            except NotFound:
                pass  # Контейнер не существует, это нормально
            
            # Подготовка переменных окружения
            environment = {
                "BOT_ID": str(bot_id),
                "API_KEY": api_key,
                "API_SECRET": api_secret,
                "CONFIG": json.dumps(bot_config, ensure_ascii=False),
                # Дополнительные переменные для логирования
                "PYTHONUNBUFFERED": "1",  # Отключение буферизации stdout
                "LOG_LEVEL": "INFO"
            }
            
            # Создание контейнера с ограничениями ресурсов
            container = self.client.containers.create(
                image="bot-runner:latest",
                name=container_name,
                environment=environment,
                detach=True,
                # Политика перезапуска при падении (кроме ручной остановки)
                restart_policy={"Name": "unless-stopped"},
                # Подключение к общей сети
                network="trading_network",
                # Ограничения ресурсов для изоляции
                mem_limit="256m",  # Максимум 256 МБ RAM
                memswap_limit="256m",  # Запрет использования swap
                cpu_quota=50000,  # 50% одного ядра CPU (из 100000)
                # Логирование в Docker (json-file driver)
                log_config={
                    "Type": "json-file",
                    "Config": {
                        "max-size": "10m",  # Максимальный размер лог-файла
                        "max-file": "3"  # Количество ротируемых файлов
                    }
                },
                # Метки для идентификации
                labels={
                    "app": "trading-bot",
                    "bot_id": str(bot_id),
                    "managed_by": "trading-backend"
                }
            )
            
            # Запуск контейнера
            container.start()
            logger.info(f"Контейнер {container_name} успешно запущен. ID: {container.id}")
            
            return container.id, None
            
        except ImageNotFound as e:
            error_msg = f"Образ не найден: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except APIError as e:
            error_msg = f"Ошибка Docker API: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Неожиданная ошибка при запуске контейнера: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def stop_bot_container(self, container_id: str) -> bool:
        """
        Остановить и удалить контейнер бота
        
        Args:
            container_id: ID Docker контейнера
            
        Returns:
            True если успешно остановлен, False при ошибке
        """
        try:
            container = self.client.containers.get(container_id)
            
            # Graceful shutdown с таймаутом 10 секунд
            logger.info(f"Останавливаю контейнер {container_id}...")
            container.stop(timeout=10)
            
            # Удаление контейнера после остановки
            logger.info(f"Удаляю контейнер {container_id}...")
            container.remove()
            
            logger.info(f"Контейнер {container_id} успешно остановлен и удален")
            return True
            
        except NotFound:
            # Контейнер уже удален - это нормально
            logger.warning(f"Контейнер {container_id} не найден (возможно уже удален)")
            return True
        except APIError as e:
            logger.error(f"Ошибка Docker API при остановке контейнера: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при остановке контейнера: {str(e)}")
            return False
    
    def get_container_logs(self, container_id: str, tail: int = 50) -> Optional[str]:
        """
        Получить логи контейнера
        
        Args:
            container_id: ID Docker контейнера
            tail: Количество последних строк логов (по умолчанию 50)
            
        Returns:
            Строка с логами или None если контейнер не найден
        """
        try:
            container = self.client.containers.get(container_id)
            
            # Получение логов с timestamps
            logs_bytes = container.logs(
                tail=tail,
                timestamps=True,
                stdout=True,
                stderr=True
            )
            
            # Декодирование из bytes в строку
            logs_string = logs_bytes.decode('utf-8', errors='replace')
            
            logger.info(f"Получены логи контейнера {container_id} ({tail} строк)")
            return logs_string
            
        except NotFound:
            logger.warning(f"Контейнер {container_id} не найден")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении логов: {str(e)}")
            return None
    
    def is_container_running(self, container_id: str) -> bool:
        """
        Проверить что контейнер запущен
        
        Args:
            container_id: ID Docker контейнера
            
        Returns:
            True если контейнер запущен, False если остановлен или не найден
        """
        try:
            container = self.client.containers.get(container_id)
            # Обновление информации о контейнере
            container.reload()
            
            is_running = container.status == "running"
            logger.debug(f"Контейнер {container_id} статус: {container.status}")
            
            return is_running
            
        except NotFound:
            logger.warning(f"Контейнер {container_id} не найден")
            return False
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса контейнера: {str(e)}")
            return False
    
    def get_container_stats(self, container_id: str) -> Optional[dict]:
        """
        Получить статистику использования ресурсов контейнера
        
        Args:
            container_id: ID Docker контейнера
            
        Returns:
            Словарь со статистикой (CPU, память, сеть) или None
        """
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # Упрощенная статистика
            return {
                "memory_usage": stats.get("memory_stats", {}).get("usage", 0),
                "memory_limit": stats.get("memory_stats", {}).get("limit", 0),
                "cpu_stats": stats.get("cpu_stats", {}),
                "networks": stats.get("networks", {})
            }
            
        except NotFound:
            logger.warning(f"Контейнер {container_id} не найден")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {str(e)}")
            return None
