"""Soportes y resistencias calculados desde los datos (velas 4H).

Método, en simple:
  1. Se buscan "pivotes": máximos y mínimos locales (un máximo más alto que las
     velas vecinas es un pivote alto; un mínimo más bajo, un pivote bajo).
  2. Los pivotes que quedan a una distancia parecida se agrupan en una zona.
  3. Cada pivote de la zona cuenta como un "toque". Solo sirven las zonas con
     MIN_TOQUES o más (tu estrategia pide 2+).
  4. Una zona bajo el precio actual es soporte; una zona sobre el precio es
     resistencia. Si el precio rompe un soporte, ese nivel pasa a ser resistencia.

Las distancias se miden en ATR (rango medio de una vela 4H), así el mismo criterio
sirve para EUR/USD, USD/JPY o USD/MXN sin tener que ajustar porcentajes.
"""

import pandas as pd

from config import (ATR_PERIODO, PIVOTE_VENTANA, MIN_TOQUES,
                    TOL_AGRUPAR_ATR, ZONA_CERCA_ATR)


def atr(c4, periodo=ATR_PERIODO):
    """ATR (rango medio verdadero) de las velas 4H. None si no hay suficientes."""
    if len(c4) < periodo + 1:
        return None
    cierre_prev = c4["close"].shift(1)
    tr = pd.concat([
        c4["high"] - c4["low"],
        (c4["high"] - cierre_prev).abs(),
        (c4["low"] - cierre_prev).abs(),
    ], axis=1).max(axis=1)
    valor = tr.rolling(periodo).mean().iloc[-1]
    return None if pd.isna(valor) else float(valor)


def pivotes(c4, ventana=PIVOTE_VENTANA):
    """Precios de los pivotes altos y bajos de las velas 4H.

    Un pivote alto es un máximo mayor que el de las `ventana` velas anteriores y
    no menor que el de las `ventana` velas siguientes (y análogo para los bajos).
    Las últimas `ventana` velas no pueden confirmarse todavía, así que se ignoran.
    """
    altos, bajos = [], []
    h, l = c4["high"].to_numpy(), c4["low"].to_numpy()
    for i in range(ventana, len(c4) - ventana):
        if h[i] > h[i - ventana:i].max() and h[i] >= h[i + 1:i + ventana + 1].max():
            altos.append(float(h[i]))
        if l[i] < l[i - ventana:i].min() and l[i] <= l[i + 1:i + ventana + 1].min():
            bajos.append(float(l[i]))
    return altos, bajos


def agrupar(precios, tolerancia):
    """Agrupa precios cercanos en zonas. Cada zona: {"precio": promedio, "toques": n}.

    Una zona no puede abarcar más de `tolerancia` de ancho.
    """
    zonas, actual = [], []
    for p in sorted(precios):
        if actual and p - actual[0] > tolerancia:
            zonas.append(actual)
            actual = []
        actual.append(p)
    if actual:
        zonas.append(actual)
    return [{"precio": round(sum(z) / len(z), 5), "toques": len(z)} for z in zonas]


def calcular_niveles(c4):
    """Zonas con MIN_TOQUES o más toques y el ATR usado.

    Retorna (niveles, atr). Si no hay datos suficientes: ([], None).
    """
    a = atr(c4)
    if a is None or a <= 0:
        return [], None
    altos, bajos = pivotes(c4)
    zonas = agrupar(altos + bajos, TOL_AGRUPAR_ATR * a)
    return [z for z in zonas if z["toques"] >= MIN_TOQUES], a


def nivel_cercano(precio, niveles, atr_valor, lado):
    """Nivel más cercano al precio por el lado pedido, si está dentro de la zona.

    lado="soporte": niveles en o bajo el precio.  lado="resistencia": sobre el precio.
    "Cerca" = a no más de ZONA_CERCA_ATR × ATR. Retorna el nivel (con su distancia
    en ATR) o None.
    """
    if not niveles or not atr_valor:
        return None
    if lado == "soporte":
        candidatos = [n for n in niveles if n["precio"] <= precio]
    else:
        candidatos = [n for n in niveles if n["precio"] > precio]
    if not candidatos:
        return None
    n = min(candidatos, key=lambda x: abs(precio - x["precio"]))
    dist = abs(precio - n["precio"]) / atr_valor
    if dist > ZONA_CERCA_ATR:
        return None
    return {**n, "dist_atr": round(dist, 2)}
