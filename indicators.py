"""Indicadores técnicos y horario seguro."""

from datetime import datetime


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


def calcular_indicadores(simbolo):
    try:
        import yfinance as yf
        datos = yf.download(simbolo, period="10d", interval="1h", progress=False)
        if datos.empty or len(datos) < 50:
            return None
        close = datos["Close"].squeeze()

        precio = round(float(close.iloc[-1]), 5)

        # RSI
        delta = close.diff()
        g = delta.where(delta > 0, 0).rolling(14).mean()
        p = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = round(float(100 - (100 / (1 + g.iloc[-1] / p.iloc[-1]))), 1)

        # EMAs
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
            "bb_upper": bb_upper, "bb_lower": bb_lower,
            "divergencia": divergencia,
        }
    except Exception:
        return None
