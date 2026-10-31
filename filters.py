"""Evaluación de filtros y cálculo del setup (entrada, SL, TP)."""

from config import SOPORTES_RESISTENCIAS, FUNDAMENTAL, MIN_TOQUES
from levels import nivel_cercano


def evaluar_filtros(par, ind):
    """Evalúa los 5 filtros de la estrategia. Retorna score y detalles."""
    precio = ind["precio"]
    rsi = ind["rsi"]
    fund = FUNDAMENTAL.get(par, "neutro")

    filtros_largo = []
    filtros_corto = []

    # ── FILTRO 1 — TENDENCIA (EMA20/50 en 4H) ──
    if ind["precio"] > ind["ema20_4h"] > ind["ema50_4h"]:
        filtros_largo.append("✅ F1: Precio sobre EMA20 y EMA50 en 4H (tendencia alcista)")
    elif ind["precio"] < ind["ema20_4h"] < ind["ema50_4h"]:
        filtros_corto.append("✅ F1: Precio bajo EMA20 y EMA50 en 4H (tendencia bajista)")
    else:
        filtros_largo.append("❌ F1: EMAs 4H sin tendencia clara")
        filtros_corto.append("❌ F1: EMAs 4H sin tendencia clara")

    # ── FILTRO 2 — NIVEL TÉCNICO (zonas calculadas, con 2+ toques) ──
    soporte = nivel_cercano(precio, ind.get("niveles"), ind.get("atr_4h"), "soporte")
    resistencia = nivel_cercano(precio, ind.get("niveles"), ind.get("atr_4h"), "resistencia")

    if soporte:
        filtros_largo.append("✅ F2: Precio cerca de soporte " + str(soporte["precio"])
                             + " (" + str(soporte["toques"]) + " toques)")
        filtros_corto.append("❌ F2: Precio en soporte (no en resistencia)")
    elif resistencia:
        filtros_corto.append("✅ F2: Precio cerca de resistencia " + str(resistencia["precio"])
                             + " (" + str(resistencia["toques"]) + " toques)")
        filtros_largo.append("❌ F2: Precio en resistencia (no en soporte)")
    else:
        filtros_largo.append("❌ F2: Sin nivel técnico claro (" + str(MIN_TOQUES) + "+ toques)")
        filtros_corto.append("❌ F2: Sin nivel técnico claro (" + str(MIN_TOQUES) + "+ toques)")

    # ── FILTRO 3 — RSI + DIVERGENCIAS ──
    if rsi < 30:
        filtros_largo.append("✅ F3: RSI=" + str(rsi) + " sobrevendido")
        filtros_corto.append("❌ F3: RSI=" + str(rsi) + " sobrevendido (no corto)")
    elif rsi > 70:
        filtros_corto.append("✅ F3: RSI=" + str(rsi) + " sobrecomprado")
        filtros_largo.append("❌ F3: RSI=" + str(rsi) + " sobrecomprado (no largo)")
    elif ind["divergencia"] == "alcista":
        filtros_largo.append("✅ F3: Divergencia alcista RSI detectada")
        filtros_corto.append("❌ F3: Divergencia alcista (no corto)")
    elif ind["divergencia"] == "bajista":
        filtros_corto.append("✅ F3: Divergencia bajista RSI detectada")
        filtros_largo.append("❌ F3: Divergencia bajista (no largo)")
    else:
        filtros_largo.append("❌ F3: RSI=" + str(rsi) + " zona neutral")
        filtros_corto.append("❌ F3: RSI=" + str(rsi) + " zona neutral")

    # ── FILTRO 4 — BOLLINGER (proxy vela confirmación) ──
    if precio <= ind["bb_lower"]:
        filtros_largo.append("✅ F4: Precio en banda inferior Bollinger")
        filtros_corto.append("❌ F4: Precio en banda inferior (no corto)")
    elif precio >= ind["bb_upper"]:
        filtros_corto.append("✅ F4: Precio en banda superior Bollinger")
        filtros_largo.append("❌ F4: Precio en banda superior (no largo)")
    else:
        filtros_largo.append("❌ F4: Precio dentro de bandas Bollinger")
        filtros_corto.append("❌ F4: Precio dentro de bandas Bollinger")

    # ── FILTRO 5 — FUNDAMENTAL + RATIO ──
    if fund == "alcista":
        filtros_largo.append("✅ F5: Sesgo fundamental alcista")
        filtros_corto.append("❌ F5: Sesgo fundamental alcista (no corto)")
    elif fund == "bajista":
        filtros_corto.append("✅ F5: Sesgo fundamental bajista")
        filtros_largo.append("❌ F5: Sesgo fundamental bajista (no largo)")
    else:
        filtros_largo.append("⚠️ F5: Fundamental neutro")
        filtros_corto.append("⚠️ F5: Fundamental neutro")

    score_largo = sum(1 for f in filtros_largo if f.startswith("✅"))
    score_corto = sum(1 for f in filtros_corto if f.startswith("✅"))

    return {
        "largo": {"score": score_largo, "filtros": filtros_largo},
        "corto": {"score": score_corto, "filtros": filtros_corto},
    }


def calcular_setup(par, ind, direccion):
    precio = ind["precio"]
    sr = SOPORTES_RESISTENCIAS.get(par, {"s": [], "r": []})

    if direccion == "largo":
        sl_ref = min(sr["s"]) if sr["s"] else precio * 0.998
        sl = round(min(sl_ref, precio * 0.998), 5)
        riesgo = precio - sl
        tp = round(precio + riesgo * 2.5, 5)
        ratio = round((tp - precio) / (precio - sl), 1)
        return {"entrada": precio, "sl": sl, "tp": tp, "ratio": ratio, "dir": "🟢 LARGO"}
    else:
        sl_ref = max(sr["r"]) if sr["r"] else precio * 1.002
        sl = round(max(sl_ref, precio * 1.002), 5)
        riesgo = sl - precio
        tp = round(precio - riesgo * 2.5, 5)
        ratio = round((precio - tp) / (sl - precio), 1)
        return {"entrada": precio, "sl": sl, "tp": tp, "ratio": ratio, "dir": "🔴 CORTO"}
