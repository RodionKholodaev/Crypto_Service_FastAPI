"""
Модуль расчета технических индикаторов
"""
import pandas as pd
import pandas_ta as ta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """Расчет технических индикаторов"""
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int) -> Optional[float]:
        """
        Расчет RSI (Relative Strength Index)
        
        Args:
            df: DataFrame с OHLCV данными
            period: период для расчета RSI
            
        Returns:
            Последнее значение RSI или None при ошибке
        """
        try:
            # Проверяем достаточно ли данных
            if len(df) < period + 10:
                logger.warning(f"Недостаточно данных для RSI: {len(df)} < {period + 10}")
                return None
            
            # Рассчитываем RSI
            rsi = ta.rsi(df['close'], length=period)
            
            if rsi is None or rsi.empty:
                logger.warning("RSI не рассчитан")
                return None
            
            # Возвращаем последнее значение
            last_rsi = float(rsi.iloc[-1])
            
            # Проверяем на NaN
            if pd.isna(last_rsi):
                logger.warning("RSI значение = NaN")
                return None
                
            return round(last_rsi, 2)
            
        except Exception as e:
            logger.error(f"Ошибка расчета RSI: {e}")
            return None
    
    @staticmethod
    def calculate_cci(df: pd.DataFrame, period: int) -> Optional[float]:
        """
        Расчет CCI (Commodity Channel Index)
        
        Args:
            df: DataFrame с OHLCV данными
            period: период для расчета CCI
            
        Returns:
            Последнее значение CCI или None при ошибке
        """
        try:
            # Проверяем достаточно ли данных
            if len(df) < period + 10:
                logger.warning(f"Недостаточно данных для CCI: {len(df)} < {period + 10}")
                return None
            
            # Рассчитываем CCI
            cci = ta.cci(df['high'], df['low'], df['close'], length=period)
            
            if cci is None or cci.empty:
                logger.warning("CCI не рассчитан")
                return None
            
            # Возвращаем последнее значение
            last_cci = float(cci.iloc[-1])
            
            # Проверяем на NaN
            if pd.isna(last_cci):
                logger.warning("CCI значение = NaN")
                return None
                
            return round(last_cci, 2)
            
        except Exception as e:
            logger.error(f"Ошибка расчета CCI: {e}")
            return None
    
    @staticmethod
    def check_signal(
        indicator_type: str,
        current_value: float,
        threshold: float,
        direction: str
    ) -> bool:
        """
        Проверка сигнала от индикатора
        
        Args:
            indicator_type: тип индикатора (RSI, CCI)
            current_value: текущее значение индикатора
            threshold: пороговое значение
            direction: направление проверки ("above" или "below")
            
        Returns:
            True если сигнал есть, False если нет
        """
        try:
            if direction == "above":
                signal = current_value > threshold
            elif direction == "below":
                signal = current_value < threshold
            else:
                logger.warning(f"Неизвестное направление: {direction}")
                return False
            
            return signal
            
        except Exception as e:
            logger.error(f"Ошибка проверки сигнала: {e}")
            return False
