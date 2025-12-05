import ccxt
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class ExchangeAPI:
    """Класс для работы с биржей через ccxt"""
    
    def __init__(self, api_key: str, api_secret: str, exchange_name: str = "bybit"):
        """
        Инициализация ccxt exchange для фьючерсной торговли
        
        Args:
            api_key: API ключ биржи
            api_secret: API секрет биржи
            exchange_name: Название биржи (по умолчанию bybit)
        """
        try:
            exchange_class = getattr(ccxt, exchange_name)
            self.exchange = exchange_class({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # Фьючерсная торговля
                    'recvWindow': 10000,  # Увеличенное окно для безопасности
                }
            })
            self.exchange_name = exchange_name
            logger.info(f"ExchangeAPI инициализирован для {exchange_name}")
        except Exception as e:
            logger.error(f"Ошибка инициализации ExchangeAPI: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Проверка работоспособности API ключей
        
        Returns:
            True если ключи рабочие, False если ошибка
        """
        try:
            # Проверяем доступ к балансу
            balance = self.exchange.fetch_balance()
            
            # Дополнительно проверяем что есть доступ к фьючерсам
            if 'USDT' not in balance:
                logger.warning("Баланс не содержит USDT")
                return False
            
            logger.info("API ключи проверены успешно")
            return True
        except ccxt.AuthenticationError as e:
            logger.error(f"Ошибка аутентификации: {e}")
            return False
        except ccxt.PermissionDenied as e:
            logger.error(f"Нет прав доступа к API: {e}")
            return False
        except ccxt.NetworkError as e:
            logger.error(f"Сетевая ошибка при проверке API: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при проверке API: {e}")
            return False
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Получить текущую цену торговой пары
        
        Args:
            symbol: Символ торговой пары (например BTC/USDT:USDT)
            
        Returns:
            Словарь с данными тикера или None при ошибке
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            logger.info(f"Получен тикер для {symbol}: {ticker.get('last', 'N/A')}")
            return ticker
        except ccxt.BadSymbol as e:
            logger.error(f"Неверный символ {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения тикера для {symbol}: {e}")
            return None
    
    def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> Optional[List]:
        """
        Получить исторические свечи для расчета индикаторов
        
        Args:
            symbol: Символ торговой пары
            timeframe: Таймфрейм (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Количество свечей (по умолчанию 100)
            
        Returns:
            Список свечей [[timestamp, open, high, low, close, volume], ...] или None
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            logger.info(f"Получено {len(ohlcv)} свечей для {symbol} {timeframe}")
            return ohlcv
        except ccxt.BadSymbol as e:
            logger.error(f"Неверный символ {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения OHLCV для {symbol} {timeframe}: {e}")
            return None
    
    def get_balance(self) -> Optional[Dict]:
        """
        Получить баланс аккаунта
        
        Returns:
            Словарь с балансом или None при ошибке
        """
        try:
            balance = self.exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error(f"Ошибка получения баланса: {e}")
            return None
