"""Configuración: correo, pares, niveles y sesgo fundamental."""

import os

GMAIL_ADDRESS  = "fmejiazugarramurdi@gmail.com"


GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")


DESTINATARIO   = "fmejiazugarramurdi@gmail.com"


PARES = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "USD/CAD": "USDCAD=X",
    "USD/CHF": "USDCHF=X",
    "EUR/JPY": "EURJPY=X",
    "EUR/GBP": "EURGBP=X",
    "AUD/USD": "AUDUSD=X",
    "NZD/USD": "NZDUSD=X",
    "USD/MXN": "USDMXN=X",
}


# OJO: el filtro F2 ya NO usa estos niveles (los calcula desde los datos, ver levels.py).
# Solo los usa calcular_setup() para el stop loss; se eliminan cuando el SL pase a ATR.
SOPORTES_RESISTENCIAS = {
    "EUR/USD": {"s": [1.1500, 1.1450], "r": [1.1630, 1.1700]},
    "GBP/USD": {"s": [1.3390, 1.3300], "r": [1.3480, 1.3550]},
    "USD/JPY": {"s": [159.00, 157.50], "r": [160.50, 162.00]},
    "USD/CAD": {"s": [1.3800, 1.3720], "r": [1.3960, 1.4050]},
    "USD/CHF": {"s": [0.7850, 0.7800], "r": [0.7950, 0.8020]},
    "EUR/JPY": {"s": [183.00, 181.00], "r": [187.00, 189.00]},
    "EUR/GBP": {"s": [0.8420, 0.8380], "r": [0.8520, 0.8580]},
    "AUD/USD": {"s": [0.6380, 0.6320], "r": [0.6480, 0.6550]},
    "NZD/USD": {"s": [0.5950, 0.5900], "r": [0.6050, 0.6120]},
    "USD/MXN": {"s": [19.00, 18.50],  "r": [19.80, 20.50]},
}


# Sesgo fundamental por par
FUNDAMENTAL = {
    "EUR/USD": "alcista",   # BCE sube tasas 11 jun
    "GBP/USD": "alcista",   # BoE hawkish
    "USD/JPY": "alcista",   # USD fuerte post NFP
    "USD/CAD": "alcista",   # USD fuerte
    "USD/CHF": "bajista",   # CHF refugio
    "EUR/JPY": "alcista",   # EUR fuerte + carry
    "EUR/GBP": "neutro",
    "AUD/USD": "neutro",
    "NZD/USD": "neutro",
    "USD/MXN": "neutro",
}


# Si DRY_RUN=1 (o true/yes), la alerta se imprime en el log y NO se envía correo.
DRY_RUN = os.environ.get("DRY_RUN", "").strip().lower() in ("1", "true", "yes")

# Historial de velas 1H que se descarga (días) y mínimo de velas 4H cerradas
# necesarias para que la EMA50 de 4H sea confiable.
PERIODO_DESCARGA = "30d"
MIN_BARRAS_4H = 60

# ── Soportes y resistencias (F2) ──
# Los valores de abajo son criterios razonables, no optimizados: se calibran en el backtest.
ATR_PERIODO = 14        # velas 4H para el ATR
PIVOTE_VENTANA = 2      # un pivote es el máximo/mínimo de 2 velas a cada lado
MIN_TOQUES = 2          # tu estrategia: soporte/resistencia con 2+ toques
TOL_AGRUPAR_ATR = 0.5   # pivotes a menos de 0.5 ATR de distancia forman una misma zona
ZONA_CERCA_ATR = 0.5    # "cerca" del nivel = a no más de 0.5 ATR
