"""
Торговый бот для фьючерсов Bybit
"""
import os
import json
import time
import logging
import ccxt
import pandas as pd
from indicators import IndicatorCalculator
from typing import Optional, Tuple

# Настройка логирования (вывод в stdout для Docker)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradingBot:
    """Торговый бот для фьючерсов"""
    
    def __init__(self):
        """Загрузка конфигурации из переменных окружения"""
        try:
            # Загрузка переменных окружения
            self.bot_id = os.getenv('BOT_ID')
            self.api_key = os.getenv('API_KEY')
            self.api_secret = os.getenv('API_SECRET')
            
            # Парсинг конфигурации
            config_str = os.getenv('CONFIG')
            self.config = json.loads(config_str)
            
            # Извлечение параметров
            self.trading_pair = self.config['trading_pair']
            self.strategy = self.config['strategy']  # "long" или "short"
            self.leverage = self.config['leverage']
            self.deposit = self.config['deposit']
            self.take_profit_percent = self.config['take_profit_percent']
            self.stop_loss_percent = self.config['stop_loss_percent']
            self.indicators = self.config['indicators']
            
            # Инициализация биржи
            self.exchange = ccxt.bybit({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'options': {'defaultType': 'future'},
                'enableRateLimit': True
            })
            
            # Переменные состояния позиции
            self.position_open = False
            self.entry_price = None
            self.position_size = None
            
            logger.info(f"✅ Бот {self.bot_id} инициализирован")
            logger.info(f"📊 Пара: {self.trading_pair}, Стратегия: {self.strategy}, Плечо: {self.leverage}x")
            logger.info(f"💰 Депозит: ${self.deposit}, TP: {self.take_profit_percent}%, SL: {self.stop_loss_percent}%")
            logger.info(f"📈 Индикаторов: {len(self.indicators)}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации бота: {e}")
            raise
    
    def set_leverage(self):
        """Установка плеча"""
        try:
            result = self.exchange.set_leverage(
                leverage=self.leverage,
                symbol=self.trading_pair
            )
            logger.info(f"⚙️ Плечо установлено: {self.leverage}x для {self.trading_pair}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка установки плеча: {e}")
            return False
    
    def check_indicators(self) -> bool:
        """
        Проверка всех индикаторов на сигнал
        
        Returns:
            True если ВСЕ индикаторы дали сигнал, иначе False
        """
        try:
            signals = []
            
            for ind in self.indicators:
                indicator_type = ind['type']
                timeframe = ind['timeframe']
                period = ind['period']
                threshold = ind['threshold']
                direction = ind['direction']
                
                logger.info(f"🔍 Проверка {indicator_type} ({timeframe}, период {period})")
                
                # Получаем OHLCV данные
                try:
                    ohlcv = self.exchange.fetch_ohlcv(
                        symbol=self.trading_pair,
                        timeframe=timeframe,
                        limit=100
                    )
                except Exception as e:
                    logger.error(f"❌ Ошибка получения данных для {indicator_type}: {e}")
                    return False
                
                # Преобразуем в DataFrame
                df = pd.DataFrame(
                    ohlcv,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                
                # Рассчитываем индикатор
                if indicator_type == "RSI":
                    value = IndicatorCalculator.calculate_rsi(df, period)
                elif indicator_type == "CCI":
                    value = IndicatorCalculator.calculate_cci(df, period)
                else:
                    logger.warning(f"⚠️ Неизвестный индикатор: {indicator_type}")
                    return False
                
                if value is None:
                    logger.warning(f"⚠️ {indicator_type} не рассчитан")
                    return False
                
                # Проверяем сигнал
                signal = IndicatorCalculator.check_signal(
                    indicator_type, value, threshold, direction
                )
                
                # Логируем результат
                if direction == "below":
                    symbol = "✓" if signal else "✗"
                    logger.info(f"   {indicator_type} ({timeframe}): {value} < {threshold} {symbol}")
                else:
                    symbol = "✓" if signal else "✗"
                    logger.info(f"   {indicator_type} ({timeframe}): {value} > {threshold} {symbol}")
                
                signals.append(signal)
            
            # Все индикаторы должны дать сигнал
            all_signals = all(signals)
            
            if all_signals:
                logger.info("✅ ВСЕ индикаторы дали сигнал на вход!")
            else:
                logger.info("⏳ Ожидание сигналов от всех индикаторов...")
            
            return all_signals
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки индикаторов: {e}")
            return False
    
    def calculate_position_size(self, current_price: float) -> float:
        """
        Расчет размера позиции
        
        Args:
            current_price: текущая цена актива
            
        Returns:
            Размер позиции в базовой валюте (например, BTC)
        """
        try:
            # Размер позиции = (депозит * плечо) / цена
            position_value = self.deposit * self.leverage
            position_size = position_value / current_price
            
            # Округляем до 3 знаков
            position_size = round(position_size, 3)
            
            logger.info(f"📊 Размер позиции: {position_size} ({position_value} USDT / {current_price})")
            
            return position_size
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета размера позиции: {e}")
            return 0.0
    
    def calculate_tp_sl_prices(self, entry_price: float) -> Tuple[float, float]:
        """
        Расчет цен Take Profit и Stop Loss
        
        Args:
            entry_price: цена входа в позицию
            
        Returns:
            Кортеж (tp_price, sl_price)
        """
        try:
            if self.strategy == "long":
                # Для long: TP выше, SL ниже
                tp_price = entry_price * (1 + self.take_profit_percent / 100)
                sl_price = entry_price * (1 - self.stop_loss_percent / 100)
            else:  # short
                # Для short: TP ниже, SL выше
                tp_price = entry_price * (1 - self.take_profit_percent / 100)
                sl_price = entry_price * (1 + self.stop_loss_percent / 100)
            
            # Округляем до 2 знаков
            tp_price = round(tp_price, 2)
            sl_price = round(sl_price, 2)
            
            logger.info(f"🎯 TP: ${tp_price}, 🛑 SL: ${sl_price}")
            
            return tp_price, sl_price
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета TP/SL: {e}")
            return 0.0, 0.0
    
    def open_position(self):
        """Открытие торговой позиции с TP/SL"""
        try:
            logger.info("🚀 Открытие позиции...")
            
            # Получаем текущую цену
            ticker = self.exchange.fetch_ticker(self.trading_pair)
            current_price = ticker['last']
            logger.info(f"💵 Текущая цена: ${current_price}")
            
            # Рассчитываем размер позиции
            position_size = self.calculate_position_size(current_price)
            if position_size <= 0:
                logger.error("❌ Размер позиции = 0, отмена открытия")
                return
            
            # Рассчитываем TP/SL
            tp_price, sl_price = self.calculate_tp_sl_prices(current_price)
            if tp_price == 0 or sl_price == 0:
                logger.error("❌ Ошибка расчета TP/SL, отмена открытия")
                return
            
            # Определяем направление ордера
            side = "buy" if self.strategy == "long" else "sell"
            
            # Создаем рыночный ордер с TP/SL
            order = self.exchange.create_order(
                symbol=self.trading_pair,
                type='market',
                side=side,
                amount=position_size,
                params={
                    'takeProfit': {
                        'triggerPrice': tp_price
                    },
                    'stopLoss': {
                        'triggerPrice': sl_price
                    }
                }
            )
            
            # Сохраняем данные позиции
            self.position_open = True
            self.entry_price = current_price
            self.position_size = position_size
            
            logger.info(f"✅ Позиция открыта: {side.upper()} {position_size} {self.trading_pair} @ ${current_price}")
            logger.info(f"   🎯 TP: ${tp_price} (+{self.take_profit_percent}%)")
            logger.info(f"   🛑 SL: ${sl_price} (-{self.stop_loss_percent}%)")
            logger.info(f"   📋 Order ID: {order.get('id', 'N/A')}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка открытия позиции: {e}")
            # Не устанавливаем position_open = True при ошибке
    
    def check_position_closed(self):
        """Проверка закрытия позиции"""
        try:
            # Получаем текущую позицию
            position = self.exchange.fetch_position(self.trading_pair)
            
            # Проверяем размер позиции
            contracts = position.get('contracts', 0)
            
            if contracts == 0 or contracts is None:
                # Позиция закрыта
                ticker = self.exchange.fetch_ticker(self.trading_pair)
                close_price = ticker['last']
                
                # Определяем был TP или SL
                tp_price, sl_price = self.calculate_tp_sl_prices(self.entry_price)
                
                if self.strategy == "long":
                    if close_price >= tp_price:
                        result = "TAKE PROFIT ✅"
                        pnl = f"+{self.take_profit_percent}%"
                    else:
                        result = "STOP LOSS ❌"
                        pnl = f"-{self.stop_loss_percent}%"
                else:  # short
                    if close_price <= tp_price:
                        result = "TAKE PROFIT ✅"
                        pnl = f"+{self.take_profit_percent}%"
                    else:
                        result = "STOP LOSS ❌"
                        pnl = f"-{self.stop_loss_percent}%"
                
                logger.info(f"🏁 Позиция закрыта по {result} @ ${close_price} ({pnl})")
                
                # Сбрасываем состояние
                self.position_open = False
                self.entry_price = None
                self.position_size = None
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки позиции: {e}")
            return False
    
    def run(self):
        """Основной цикл бота"""
        try:
            logger.info("=" * 60)
            logger.info(f"🚀 Бот {self.bot_id} запущен")
            logger.info(f"📊 Пара: {self.trading_pair}")
            logger.info(f"📈 Стратегия: {self.strategy.upper()}")
            logger.info(f"⚙️ Плечо: {self.leverage}x")
            logger.info(f"💰 Депозит: ${self.deposit}")
            logger.info("=" * 60)
            
            # Устанавливаем плечо
            self.set_leverage()
            
            # Основной цикл
            while True:
                try:
                    if self.position_open:
                        # Позиция открыта - проверяем закрылась ли
                        logger.info("⏳ Позиция открыта, мониторинг закрытия...")
                        self.check_position_closed()
                        time.sleep(10)
                        
                    else:
                        # Позиции нет - проверяем индикаторы
                        logger.info("🔍 Проверка индикаторов...")
                        
                        if self.check_indicators():
                            # Все индикаторы дали сигнал - открываем позицию
                            self.open_position()
                        
                        time.sleep(10)
                
                except ccxt.NetworkError as e:
                    logger.error(f"🌐 Проблема с сетью: {e}")
                    logger.info("⏳ Ожидание 60 секунд перед повтором...")
                    time.sleep(60)
                    
                except ccxt.ExchangeError as e:
                    logger.error(f"⚠️ Ошибка биржи: {e}")
                    logger.info("⏳ Ожидание 60 секунд перед повтором...")
                    time.sleep(60)
                    
                except Exception as e:
                    logger.error(f"❌ Неожиданная ошибка: {e}")
                    time.sleep(10)
        
        except KeyboardInterrupt:
            logger.info("🛑 Бот остановлен пользователем")
        
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}")
            raise


if __name__ == '__main__':
    bot = TradingBot()
    bot.run()
