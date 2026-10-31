"""Pruebas del filtro F1 (tendencia EMA20/EMA50 en 4H real).

Usan series sintéticas, así que no necesitan internet ni Yahoo Finance.
Ejecutar desde la raíz del repo:  python -m pytest -q
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from indicators import ema_4h, indicadores_desde_serie  # noqa: E402
from filters import evaluar_filtros                     # noqa: E402


def serie(valores, fin):
    """Serie de cierres 1H que termina en `fin` (UTC)."""
    idx = pd.date_range(end=pd.Timestamp(fin, tz="UTC"), periods=len(valores), freq="1h")
    return pd.Series(valores, index=idx)


def ruido(n, escala=0.0002, semilla=0):
    return np.random.default_rng(semilla).normal(0, escala, n)


def f1(resultado, direccion):
    return [x for x in resultado[direccion]["filtros"] if "F1" in x][0]


# ── Armado de las velas 4H ──────────────────────────────────────────────

def test_ema_4h_coincide_con_calculo_manual():
    # Termina a las 03:00 → la última vela 4H (00:00–03:00) está completa.
    c = serie(1.10 + np.cumsum(ruido(400, 0.0005, 1)), "2026-10-30 03:00")
    c4 = c.groupby(c.index.floor("4h")).last()
    esperado20 = round(float(c4.ewm(span=20).mean().iloc[-1]), 5)
    esperado50 = round(float(c4.ewm(span=50).mean().iloc[-1]), 5)

    ema20, ema50, n = ema_4h(c)

    assert (ema20, ema50, n) == (esperado20, esperado50, len(c4))


def test_descarta_la_vela_4h_en_formacion():
    # Termina a las 05:00 → la vela 04:00–07:00 solo tiene 2 de 4 horas.
    c = serie(1.10 + np.cumsum(ruido(400, 0.0005, 2)), "2026-10-30 05:00")
    sin_parcial = c.iloc[:-2]            # sin las 04:00 y 05:00

    assert ema_4h(c) == ema_4h(sin_parcial)


def test_historial_insuficiente_devuelve_none():
    c = serie(1.10 + ruido(100), "2026-10-30 03:00")   # ≈ 25 velas 4H, faltan

    assert ema_4h(c) is None
    assert indicadores_desde_serie(c) is None


# ── Filtro F1 ───────────────────────────────────────────────────────────

def test_tendencia_alcista_clara_da_f1_largo():
    c = serie(np.linspace(1.10, 1.16, 500) + ruido(500, semilla=3), "2026-10-30 07:00")
    ind = indicadores_desde_serie(c)

    r = evaluar_filtros("EUR/USD", ind)

    assert f1(r, "largo").startswith("✅")


def test_tendencia_bajista_clara_da_f1_corto():
    c = serie(np.linspace(1.16, 1.10, 500) + ruido(500, semilla=4), "2026-10-30 07:00")
    ind = indicadores_desde_serie(c)

    r = evaluar_filtros("EUR/USD", ind)

    assert f1(r, "corto").startswith("✅")


def test_rebote_corto_en_1h_dentro_de_bajista_4h_no_da_f1_largo():
    """El error del motor anterior: un rebote de 1H se leía como 'tendencia alcista'
    aunque en 4H la EMA20 seguía bajo la EMA50 (tendencia bajista)."""
    bajada = np.linspace(1.17, 1.13, 400)
    rebote = np.linspace(1.13, 1.13 + 0.0007 * 20, 20)
    c = serie(np.concatenate([bajada, rebote]) + ruido(420, semilla=5), "2026-10-30 07:00")
    ind = indicadores_desde_serie(c)

    # Criterio antiguo (EMAs en 1H): lo habría marcado como alcista.
    assert ind["precio"] > ind["ema20"] > ind["ema50"]
    # En 4H la tendencia sigue siendo bajista.
    assert ind["ema20_4h"] < ind["ema50_4h"]

    r = evaluar_filtros("EUR/USD", ind)

    assert f1(r, "largo").startswith("❌")
