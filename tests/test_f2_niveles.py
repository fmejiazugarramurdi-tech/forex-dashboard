"""Pruebas del filtro F2 (soportes y resistencias calculados, con 2+ toques).

Usan series sintéticas, así que no necesitan internet ni Yahoo Finance.
Ejecutar desde la raíz del repo:  python -m pytest -q
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from indicators import indicadores_desde_serie   # noqa: E402
from filters import evaluar_filtros              # noqa: E402
from levels import agrupar, calcular_niveles, nivel_cercano, pivotes  # noqa: E402


def ohlc_desde_4h(barras, fin="2026-10-30 03:00"):
    """barras: lista de (high, low, close) por vela 4H → series 1H (close, high, low).

    Cada vela 4H se reparte en 4 velas de 1H para que, al volver a armar las 4H,
    queden exactamente ese máximo, mínimo y cierre.
    """
    c, h, l = [], [], []
    for hi, lo, cl in barras:
        c += [cl] * 4
        h += [hi, cl, cl, cl]
        l += [cl, lo, cl, cl]
    idx = pd.date_range(end=pd.Timestamp(fin, tz="UTC"), periods=len(c), freq="1h")
    return pd.Series(c, idx), pd.Series(h, idx), pd.Series(l, idx)


def oscilacion(n, centro, amplitud, periodo=20, fase=5):
    """Cierres que oscilan entre centro±amplitud, con mínimos cada `periodo` velas."""
    t = np.arange(n)
    return centro + amplitud * np.sin(2 * np.pi * (t - fase) / periodo - np.pi / 2)


def f2(resultado, direccion):
    return [x for x in resultado[direccion]["filtros"] if "F2" in x][0]


# ── Piezas del cálculo ──────────────────────────────────────────────────

def test_pivotes_detecta_maximos_y_minimos_locales():
    alto = np.array([1, 2, 3, 2, 1, 2, 3, 2, 1], dtype=float)
    c4 = pd.DataFrame({"high": alto, "low": alto - 0.5})

    altos, bajos = pivotes(c4, ventana=2)

    assert altos == [3.0, 3.0]
    assert bajos == [0.5]


def test_agrupar_junta_precios_cercanos_y_cuenta_toques():
    zonas = agrupar([1.1000, 1.1004, 1.1100, 1.1102, 1.1103, 1.1200], tolerancia=0.001)

    assert [z["toques"] for z in zonas] == [2, 3, 1]
    assert zonas[0]["precio"] == 1.1002


def test_un_solo_toque_no_forma_nivel():
    # Baja y sube en línea recta: un único mínimo (1 toque) y ningún máximo.
    cierre = list(np.linspace(1.12, 1.10, 30)) + list(np.linspace(1.10, 1.12, 30))
    c4 = pd.DataFrame({"close": cierre,
                       "high": [x + 0.0005 for x in cierre],
                       "low": [x - 0.0005 for x in cierre]})

    niveles, atr = calcular_niveles(c4)

    assert atr is not None
    assert niveles == []          # 1 toque no alcanza: tu estrategia pide 2+


# ── Filtro F2 con datos completos ───────────────────────────────────────

def test_precio_cerca_de_un_piso_con_varios_toques_da_f2_largo():
    cierre = oscilacion(110, centro=1.1450, amplitud=0.0050)
    barras = [(x + 0.0005, x - 0.0005, x) for x in cierre]
    barras[-1] = (1.14070, 1.13990, 1.14020)          # última vela cerca del piso
    ind = indicadores_desde_serie(*ohlc_desde_4h(barras))

    r = evaluar_filtros("EUR/USD", ind)

    assert f2(r, "largo").startswith("✅ F2: Precio cerca de soporte")
    assert f2(r, "corto").startswith("❌")
    assert any(n["toques"] >= 2 and abs(n["precio"] - 1.1395) < 0.0005 for n in ind["niveles"])


def test_soporte_roto_lejos_ya_no_cuenta_como_soporte():
    """Caso de la alerta del 30-jun: el motor viejo (niveles a mano, tolerancia 0.3%)
    marcaba 'cerca de soporte' un nivel que el precio ya había perdido."""
    cierre = list(oscilacion(90, centro=1.1500, amplitud=0.0050))
    barras = [(x + 0.0005, x - 0.0005, x) for x in cierre]
    for x in (1.1440, 1.1432, 1.1428, 1.1427, 1.1427):    # rompe el piso y cae
        barras.append((x + 0.0004, x - 0.0004, x))
    ind = indicadores_desde_serie(*ohlc_desde_4h(barras))
    piso = min(ind["niveles"], key=lambda n: abs(n["precio"] - 1.1450))

    # Criterio antiguo: |precio − nivel| / nivel < 0.3% → lo daba por bueno.
    assert abs(ind["precio"] - piso["precio"]) / piso["precio"] < 0.003

    r = evaluar_filtros("EUR/USD", ind)

    assert f2(r, "largo").startswith("❌")


def test_nivel_recien_roto_pasa_a_ser_resistencia():
    cierre = list(oscilacion(90, centro=1.1500, amplitud=0.0050))
    barras = [(x + 0.0005, x - 0.0005, x) for x in cierre]
    for x in (1.1440, 1.1436, 1.1438, 1.1437, 1.1438):    # justo bajo el piso roto
        barras.append((x + 0.0004, x - 0.0004, x))
    ind = indicadores_desde_serie(*ohlc_desde_4h(barras))

    r = evaluar_filtros("EUR/USD", ind)

    assert f2(r, "largo").startswith("❌ F2: Precio en resistencia")
    assert f2(r, "corto").startswith("✅ F2: Precio cerca de resistencia")


def test_sin_maximos_y_minimos_no_hay_nivel_y_el_filtro_falla():
    cierre = oscilacion(110, centro=1.1450, amplitud=0.0050)
    c, _, _ = ohlc_desde_4h([(x + 0.0005, x - 0.0005, x) for x in cierre])

    ind = indicadores_desde_serie(c)          # sin high/low

    assert ind["niveles"] == [] and ind["atr_4h"] is None
    r = evaluar_filtros("EUR/USD", ind)
    assert f2(r, "largo").startswith("❌ F2: Sin nivel técnico claro")


def test_nivel_cercano_respeta_el_lado_y_la_distancia():
    niveles = [{"precio": 1.1000, "toques": 3}, {"precio": 1.1100, "toques": 2}]
    atr = 0.002                                  # zona "cerca" = 0.5 × ATR = 0.001

    assert nivel_cercano(1.1005, niveles, atr, "soporte")["precio"] == 1.1000
    assert nivel_cercano(1.0995, niveles, atr, "soporte") is None        # bajo el nivel
    assert nivel_cercano(1.0995, niveles, atr, "resistencia")["precio"] == 1.1000
    assert nivel_cercano(1.1050, niveles, atr, "soporte") is None        # muy lejos
