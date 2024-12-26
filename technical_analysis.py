import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, SMAIndicator, EMAIndicator, CCIIndicator
from ta.volatility import BollingerBands
from ta.volume import VolumeWeightedAveragePrice

def calculate_indicators(df):
    # RSI (Индекс на релативна сила)
    df['RSI'] = RSIIndicator(close=df['Цена на последна трансакција'], window=14).rsi()

    # Стохастички осцилатор
    df['Стохастички осцилатор'] = StochasticOscillator(
        high=df['Мак.'], low=df['Мин.'], close=df['Цена на последна трансакција'], window=14
    ).stoch()

    # MACD (Преместен просек на дивергенција на конвергенција)
    macd = MACD(close=df['Цена на последна трансакција'])
    df['MACD'] = macd.macd()
    df['MACD_сигнал'] = macd.macd_signal()
    df['MACD_хистограм'] = macd.macd_diff()

    # SMA и EMA (Едноставен и експоненцијален преместен просек)
    df['SMA_20'] = SMAIndicator(close=df['Цена на последна трансакција'], window=20).sma_indicator()
    df['EMA_20'] = EMAIndicator(close=df['Цена на последна трансакција'], window=20).ema_indicator()

    # Bollinger Bands (Болинџерови опсези)
    bollinger = BollingerBands(close=df['Цена на последна трансакција'], window=20)
    df['Горна граница Болинџер'] = bollinger.bollinger_hband()
    df['Долна граница Болинџер'] = bollinger.bollinger_lband()

    # CCI (Индекс на канал на стока)
    df['CCI'] = CCIIndicator(high=df['Мак.'], low=df['Мин.'], close=df['Цена на последна трансакција'], window=20).cci()

    return df
