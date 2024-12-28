import pandas as pd
import numpy as np
from models import db
from sqlalchemy import text

def generate_signal(
        rsi, macd_histogram, last_price, upper_band, lower_band,
        moving_average, ema, atr, stochastic, cci, williams_r
):
    # Thresholds for decision-making
    rsi_buy_threshold = 30
    rsi_sell_threshold = 70
    macd_threshold = 0  # Positive: Bullish, Negative: Bearish
    stochastic_threshold = 20  # Buy if < 20, Sell if > 80
    cci_buy_threshold = -100
    cci_sell_threshold = 100
    williams_buy_threshold = -80
    williams_sell_threshold = -20

    # Initialize counters for Buy/Sell signals
    buy_signals = 0
    sell_signals = 0

    # RSI Signal
    if rsi < rsi_buy_threshold:
        buy_signals += 1
    elif rsi > rsi_sell_threshold:
        sell_signals += 1

    # MACD Histogram Signal
    if macd_histogram > macd_threshold:
        buy_signals += 1
    elif macd_histogram < macd_threshold:
        sell_signals += 1

    # Bollinger Bands Signal
    if last_price <= lower_band:
        buy_signals += 1
    elif last_price >= upper_band:
        sell_signals += 1

    # Moving Average Signal
    if last_price > moving_average:
        buy_signals += 1
    elif last_price < moving_average:
        sell_signals += 1

    # Exponential Moving Average (EMA) Signal
    if last_price > ema:
        buy_signals += 1
    elif last_price < ema:
        sell_signals += 1

    # Average True Range (ATR): Use as a volatility filter
    # Example: No action if ATR is very low (market not moving)
    if atr > 0:  # Include specific thresholds if needed
        pass  # Placeholder for ATR-based logic

    # Stochastic Oscillator Signal
    if stochastic < stochastic_threshold:
        buy_signals += 1
    elif stochastic > 100 - stochastic_threshold:
        sell_signals += 1

    # Commodity Channel Index (CCI) Signal
    if cci < cci_buy_threshold:
        buy_signals += 1
    elif cci > cci_sell_threshold:
        sell_signals += 1

    # Williams %R Signal
    if williams_r < williams_buy_threshold:
        buy_signals += 1
    elif williams_r > williams_sell_threshold:
        sell_signals += 1

    # Final Signal Decision
    if buy_signals > sell_signals:
        return "Buy"
    elif sell_signals > buy_signals:
        return "Sell"
    else:
        return "Hold"


# RSI - Relative Strength Index
def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# Moving Average (MA)
def calculate_moving_average(prices, window=5):
    return prices.rolling(window=window).mean()






