"""Indicadores técnicos y horario seguro."""

from datetime import datetime

import pandas as pd

from config import PERIODO_DESCARGA, MIN_BARRAS_4H
from levels import calcular_niveles


def es_horario_seguro():
    """Evita sesión asiática (00:00-07:00 hora Chile GMT-3) y fin de semana."""
    ahora = datetime.utcnow()
    # Fin de semana
    if ahora.weekday() >= 5:
        return False
    # Sesión asiática: 03:00-10:00 UTC = 00:00-07:00 Chile GMT-3
    if 3 <= ahora.hour < 10:
        return False
    return True


def velas_4h(close, high=None, low=None):
    """Velas 4H cerradas, armadas a partir de datos de 1H.

    Si se pasan `high` y `low`, incluye máximos y mínimos (necesarios para niveles
    y ATR). Si la última vela 4H está en formación, se descarta, para que nada
    cambie mientras esa vela todavía se mueve. Retorna un DataFrame o None.
    """
    df = pd.DataFrame({"close": close.resample("4h").last()})
    if high is not None and low is not None:
        df["high"] = high.resample("4h").max()
        df["low"] = low.resample("4h").min()
    df = df.dropna()
    if df.empty:
        return None
    # La vela 4H está completa si ya llegó su última hora (inicio + 3h).
    if close.index[-1] < df.index[-1] + pd.Timedelta(hours=3):
        df = df.iloc[:-1]
    return df if len(df) else None


def ema_4h(close):
    """EMA20 y EMA50 sobre velas de 4H cerradas.

    Retorna (ema20, ema50, n_barras) o None si no hay historial suficiente.
    """
    c4 = velas_4h(close)
    if c4 is None or len(c4) < MIN_BARRAS_4H:
        return None
    ema20 = round(float(c4["close"].ewm(span=20).mean().iloc[-1]), 5)
    ema50 = round(float(c4["close"].ewm(span=50).mean().iloc[-1]), 5)
    return ema20, ema50, len(c4)


def indicadores_desde_serie(close, high=None, low=None):
    """Calcula todos los indicadores a partir de series de 1H (cierre, máximo, mínimo).

    Sin `high`/`low` no se pueden calcular niveles: el F2 quedará sin nivel claro.
    """
    e4 = ema_4h(close)
    if e4 is None:
        return None
    ema20_4h, ema50_4h, barras_4h = e4

    niveles, atr_4h = [], None
    if high is not None and low is not None:
        niveles, atr_4h = calcular_niveles(velas_4h(close, high, low))

    precio = round(float(close.iloc[-1]), 5)

    # RSI
    delta = close.diff()
    g = delta.where(delta > 0, 0).rolling(14).mean()
    p = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = round(float(100 - (100 / (1 + g.iloc[-1] / p.iloc[-1]))), 1)

    # EMAs en 1H (referencia; el filtro de tendencia F1 usa las de 4H)
    ema20 = round(float(close.ewm(span=20).mean().iloc[-1]), 5)
    ema50 = round(float(close.ewm(span=50).mean().iloc[-1]), 5)

    # Bollinger Bands
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_upper = round(float((sma20 + 2*std20).iloc[-1]), 5)
    bb_lower = round(float((sma20 - 2*std20).iloc[-1]), 5)

    # Divergencia RSI simple
    rsi_series = 100 - (100 / (1 + g / p))
    divergencia = None
    if len(close) >= 10:
        if close.iloc[-1] > close.iloc[-5] and rsi_series.iloc[-1] < rsi_series.iloc[-5]:
            divergencia = "bajista"
        elif close.iloc[-1] < close.iloc[-5] and rsi_series.iloc[-1] > rsi_series.iloc[-5]:
            divergencia = "alcista"

    return {
        "precio": precio, "rsi": rsi,
        "ema20": ema20, "ema50": ema50,
        "ema20_4h": ema20_4h, "ema50_4h": ema50_4h, "barras_4h": barras_4h,
        "bb_upper": bb_upper, "bb_lower": bb_lower,
        "divergencia": divergencia,
        "niveles": niveles, "atr_4h": atr_4h,
    }


def calcular_indicadores(simbolo):
    try:
        import yfinance as yf
        datos = yf.download(simbolo, period=PERIODO_DESCARGA, interval="1h", progress=False)
        if datos.empty or len(datos) < 50:
            return None
        close = datos["Close"].squeeze()
        high = datos["High"].squeeze()
        low = datos["Low"].squeeze()
        return indicadores_desde_serie(close, high, low)
    except Exception:
        return None
