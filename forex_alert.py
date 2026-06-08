"""
=============================================================
  FOREX ALERT SYSTEM — Felipe Mejía
  Monitorea 10 pares cada hora
  Envía alerta cuando se cumplen 4/5 o 5/5 filtros
  fmejiazugarramurdi@gmail.com
=============================================================
"""

import smtplib, ssl, os, re, urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

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


def evaluar_filtros(par, ind):
    """Evalúa los 5 filtros de la estrategia. Retorna score y detalles."""
    sr = SOPORTES_RESISTENCIAS.get(par, {"s": [], "r": []})
    precio = ind["precio"]
    rsi = ind["rsi"]
    fund = FUNDAMENTAL.get(par, "neutro")

    filtros_largo = []
    filtros_corto = []

    # ── FILTRO 1 — TENDENCIA (EMA20/50) ──
    if ind["precio"] > ind["ema20"] > ind["ema50"]:
        filtros_largo.append("✅ F1: Precio sobre EMA20 y EMA50 (tendencia alcista)")
    elif ind["precio"] < ind["ema20"] < ind["ema50"]:
        filtros_corto.append("✅ F1: Precio bajo EMA20 y EMA50 (tendencia bajista)")
    else:
        filtros_largo.append("❌ F1: EMAs sin tendencia clara")
        filtros_corto.append("❌ F1: EMAs sin tendencia clara")

    # ── FILTRO 2 — NIVEL TÉCNICO ──
    cerca_soporte = any(abs(precio - s) / s < 0.003 for s in sr["s"])
    cerca_resistencia = any(abs(precio - r) / r < 0.003 for r in sr["r"])

    if cerca_soporte:
        filtros_largo.append("✅ F2: Precio cerca de soporte clave")
        filtros_corto.append("❌ F2: Precio en soporte (no en resistencia)")
    elif cerca_resistencia:
        filtros_corto.append("✅ F2: Precio cerca de resistencia clave")
        filtros_largo.append("❌ F2: Precio en resistencia (no en soporte)")
    else:
        filtros_largo.append("❌ F2: Sin nivel técnico claro")
        filtros_corto.append("❌ F2: Sin nivel técnico claro")

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


def construir_html_alerta(oportunidades):
    ahora = datetime.utcnow().strftime("%A %d de %B, %Y — %H:%M UTC")

    filas = ""
    for op in oportunidades:
        color = "#00aa55" if "LARGO" in op["setup"]["dir"] else "#ff4444"
        fuerza = "⭐⭐⭐⭐⭐ SEÑAL FUERTE" if op["score"] == 5 else "⭐⭐⭐⭐ SEÑAL MODERADA"
        tam = "1% capital" if op["score"] == 5 else "0.5% capital"
        filtros_html = "<br>".join(op["filtros"])
        filas += (
            "<tr style='border-bottom:2px solid #222;'>"
            "<td style='padding:12px;font-size:18px;font-weight:bold;color:#fff;'>" + op["par"] + "</td>"
            "<td style='padding:12px;font-weight:bold;color:" + color + ";font-size:16px;'>" + op["setup"]["dir"] + "</td>"
            "<td style='padding:12px;color:#fff;'>" + str(op["setup"]["entrada"]) + "</td>"
            "<td style='padding:12px;color:#ff6666;'>" + str(op["setup"]["sl"]) + "</td>"
            "<td style='padding:12px;color:#00cc88;'>" + str(op["setup"]["tp"]) + "</td>"
            "<td style='padding:12px;color:#ffcc00;'>" + str(op["setup"]["ratio"]) + ":1</td>"
            "<td style='padding:12px;color:#aaa;font-size:12px;'>" + tam + "</td>"
            "</tr>"
            "<tr style='background:#1a1a1a;'>"
            "<td colspan='7' style='padding:10px 12px;'>"
            "<div style='font-size:12px;color:#888;margin-bottom:4px;'>" + fuerza + " — " + str(op["score"]) + "/5 filtros</div>"
            "<div style='font-size:12px;color:#aaa;line-height:1.8;'>" + filtros_html + "</div>"
            "</td></tr>"
        )

    return (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'></head>"
        "<body style='margin:0;padding:0;background:#0d0d0d;font-family:Arial,sans-serif;color:#e0e0e0;'>"
        "<table width='100%' style='max-width:750px;margin:0 auto;background:#111;border-radius:10px;overflow:hidden;'>"
        "<tr><td style='background:linear-gradient(135deg,#1a0a0a,#3a0000);padding:24px 28px;border-bottom:3px solid #ff4444;'>"
        "<h1 style='margin:0;font-size:24px;color:#ff6666;'>🚨 ALERTA DE TRADING — OPORTUNIDAD DETECTADA</h1>"
        "<p style='margin:8px 0 0;color:#ffaaaa;font-size:13px;'>" + ahora + " — Sistema automático Felipe Mejía</p>"
        "</td></tr>"
        "<tr><td style='padding:20px 28px;'>"
        "<h2 style='margin:0 0 12px;font-size:15px;color:#ffcc00;'>⚡ " + str(len(oportunidades)) + " OPORTUNIDAD(ES) CON 4+ FILTROS</h2>"
        "<table width='100%' style='border-collapse:collapse;font-size:13px;'>"
        "<tr style='background:#1a1a2e;color:#aaa;'>"
        "<th style='padding:10px;text-align:left;'>Par</th>"
        "<th style='padding:10px;text-align:left;'>Dirección</th>"
        "<th style='padding:10px;text-align:left;'>Entrada</th>"
        "<th style='padding:10px;text-align:left;'>Stop Loss</th>"
        "<th style='padding:10px;text-align:left;'>Take Profit</th>"
        "<th style='padding:10px;text-align:left;'>Ratio</th>"
        "<th style='padding:10px;text-align:left;'>Tamaño</th>"
        "</tr>"
        + filas +
        "</table></td></tr>"
        "<tr><td style='padding:16px 28px;background:#0f2a0f;border-top:1px solid #1a4a1a;'>"
        "<p style='margin:0;font-size:13px;color:#aaffaa;line-height:1.8;'>"
        "⚠️ <strong>Recuerda:</strong> Confirma siempre con una vela de confirmación en XTB antes de entrar.<br>"
        "Estos setups cumplen 4/5 o 5/5 filtros de tu estrategia — el filtro 4 (vela) debes confirmarlo visualmente."
        "</p></td></tr>"
        "<tr><td style='padding:12px 28px;background:#0a0a0a;text-align:center;'>"
        "<p style='margin:0;font-size:11px;color:#444;'>Sistema de alertas automático — Felipe Mejía • No es asesoría financiera</p>"
        "</td></tr></table></body></html>"
    )


def enviar_alerta(oportunidades):
    if not GMAIL_PASSWORD:
        print("❌ Contraseña no configurada.")
        return

    ahora = datetime.utcnow()
    pares_str = ", ".join(op["par"] for op in oportunidades)
    asunto = "🚨 ALERTA FOREX — " + str(len(oportunidades)) + " oportunidad(es): " + pares_str

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = DESTINATARIO
    msg.attach(MIMEText(construir_html_alerta(oportunidades), "html"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
            server.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, DESTINATARIO, msg.as_string())
        print("✅ Alerta enviada: " + pares_str)
    except Exception as e:
        print("❌ Error: " + str(e))


def main():
    print("=" * 50)
    print("  FOREX ALERT — " + datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"))
    print("=" * 50)

    if not es_horario_seguro():
        print("⏸️ Sesión asiática o fin de semana — no se monitorea.")
        return

    oportunidades = []

    for par, simbolo in PARES.items():
        print("📡 Analizando " + par + "...")
        ind = calcular_indicadores(simbolo)
        if not ind:
            print("  ⚠️ Sin datos")
            continue

        resultado = evaluar_filtros(par, ind)

        for direccion in ["largo", "corto"]:
            score = resultado[direccion]["score"]
            if score >= 4:
                setup = calcular_setup(par, ind, direccion)
                if setup["ratio"] >= 2:
                    oportunidades.append({
                        "par": par,
                        "score": score,
                        "setup": setup,
                        "filtros": resultado[direccion]["filtros"],
                        "ind": ind,
                    })
                    print("  🎯 " + par + " " + direccion.upper() + " — " + str(score) + "/5 filtros")

    if oportunidades:
        oportunidades.sort(key=lambda x: x["score"], reverse=True)
        enviar_alerta(oportunidades)
    else:
        print("✅ Sin oportunidades claras esta hora.")


if __name__ == "__main__":
    main()
