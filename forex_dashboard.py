"""
=============================================================
  FOREX DAILY DASHBOARD — Felipe Mejía
  Datos en vivo via Yahoo Finance + Indicadores técnicos
  Envía a fmejiazugarramurdi@gmail.com — Lunes a Viernes 18:30
=============================================================
"""

import smtplib, ssl, os, re, urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ── CONFIGURACIÓN ──────────────────────────────────────────
GMAIL_ADDRESS  = "fmejiazugarramurdi@gmail.com"
GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
DESTINATARIO   = "fmejiazugarramurdi@gmail.com"
# ───────────────────────────────────────────────────────────

PARES = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "USD/CHF": "USDCHF=X",
    "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X",
}

SOPORTES_RESISTENCIAS = {
    "EUR/USD": {"s": ["1.1580", "1.1500"], "r": ["1.1683", "1.1750"]},
    "GBP/USD": {"s": ["1.3390", "1.3300"], "r": ["1.3480", "1.3550"]},
    "USD/JPY": {"s": ["154.00", "152.50"], "r": ["161.00", "163.00"]},
    "USD/CHF": {"s": ["0.7850", "0.7800"], "r": ["0.7950", "0.8000"]},
    "EUR/GBP": {"s": ["0.8450", "0.8400"], "r": ["0.8520", "0.8580"]},
    "EUR/JPY": {"s": ["183.00", "181.50"], "r": ["187.00", "189.00"]},
}

EVENTOS_SEMANA = [
    {"dia": "Lunes 2 jun",    "hora": "15:45", "evento": "ISM Manufacturing PMI (EE.UU.)",   "impacto": "🔴 ALTO",     "par": "USD todos"},
    {"dia": "Martes 3 jun",   "hora": "15:45", "evento": "ISM Services PMI (EE.UU.)",        "impacto": "🔴 ALTO",     "par": "USD todos"},
    {"dia": "Miércoles 4 jun","hora": "TBD",   "evento": "Hablan miembros Fed",              "impacto": "🟡 MEDIO",    "par": "USD todos"},
    {"dia": "Jueves 5 jun",   "hora": "09:00", "evento": "PMI Servicios Eurozona",           "impacto": "🟡 MEDIO",    "par": "EUR/USD"},
    {"dia": "Jueves 5 jun",   "hora": "14:30", "evento": "Jobless Claims EE.UU.",            "impacto": "🟡 MEDIO",    "par": "USD todos"},
    {"dia": "Viernes 6 jun",  "hora": "14:30", "evento": "⚡ NFP — Nóminas No Agrícolas",  "impacto": "🔴🔴 MÁXIMO", "par": "TODOS"},
    {"dia": "Viernes 6 jun",  "hora": "14:30", "evento": "Tasa de desempleo EE.UU.",        "impacto": "🔴 ALTO",     "par": "USD todos"},
    {"dia": "Viernes 6 jun",  "hora": "11:00", "evento": "CPI Flash Eurozona",              "impacto": "🔴 ALTO",     "par": "EUR/USD"},
]

CONTEXTO_MACRO = """• 💵 DXY (~99): Presión bajista estructural. Fed en pausa. Nuevo Chair Warsh: dovish = USD negativo.
• 🏦 FED: Tasa 3.50%-3.75%. Próximo FOMC 16-17 junio — primer dot plot bajo Warsh.
• 🏦 BCE: Preparando posible subida de tasas en junio = soporte para EUR.
• ⚡ RIESGO: Tensiones EE.UU.-Irán. Petróleo elevado = presión inflacionaria global."""


def calcular_indicadores(simbolo):
    try:
        import yfinance as yf
        datos = yf.download(simbolo, period="10d", interval="1h", progress=False)
        if datos.empty:
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

        # SEÑAL
        score = 0
        razones = []

        if precio > ema20 > ema50:
            score += 1; razones.append("✅ Precio sobre EMA20 y EMA50")
        elif precio < ema20 < ema50:
            score -= 1; razones.append("❌ Precio bajo EMA20 y EMA50")

        if rsi < 35:
            score += 1; razones.append(f"✅ RSI={rsi} sobrevendido → posible rebote")
        elif rsi > 65:
            score -= 1; razones.append(f"❌ RSI={rsi} sobrecomprado → posible caída")
        else:
            razones.append(f"⚠️ RSI={rsi} zona neutral")

        if precio <= bb_lower:
            score += 1; razones.append("✅ Precio en banda inferior Bollinger")
        elif precio >= bb_upper:
            score -= 1; razones.append("❌ Precio en banda superior Bollinger")

        if score >= 2:
            sesgo = "🟢 LARGO"; color = "#00aa55"
        elif score <= -2:
            sesgo = "🔴 CORTO"; color = "#ff4444"
        else:
            sesgo = "⚠️ NEUTRO"; color = "#ffaa00"

        return {
            "precio": precio, "rsi": rsi,
            "ema20": ema20, "ema50": ema50,
            "bb_upper": bb_upper, "bb_lower": bb_lower,
            "sesgo": sesgo, "color": color,
            "score": score, "razones": razones
        }
    except Exception as e:
        return None


def calcular_setup(par, ind):
    sr = SOPORTES_RESISTENCIAS.get(par, {})
    soportes = sr.get("s", [])
    resistencias = sr.get("r", [])
    p = ind["precio"]

    if "LARGO" in ind["sesgo"]:
        sl_pips = round(p * 0.002, 5)
        tp_pips = round(p * 0.004, 5)
        return {
            "direccion": "🟢 LARGO",
            "entrada": p,
            "sl": round(p - sl_pips, 5),
            "tp": round(p + tp_pips, 5),
            "tf": "1H o 4H",
        }
    elif "CORTO" in ind["sesgo"]:
        sl_pips = round(p * 0.002, 5)
        tp_pips = round(p * 0.004, 5)
        return {
            "direccion": "🔴 CORTO",
            "entrada": p,
            "sl": round(p + sl_pips, 5),
            "tp": round(p - tp_pips, 5),
            "tf": "1H o 4H",
        }
    return None


def evento_hoy():
    hoy = datetime.now()
    dias = {0:"Lunes", 1:"Martes", 2:"Miércoles", 3:"Jueves", 4:"Viernes"}
    dia_str = f"{dias.get(hoy.weekday(),'')} {hoy.day}"
    return [e for e in EVENTOS_SEMANA if dia_str.lower() in e["dia"].lower()]


def nivel_alerta():
    hoy = evento_hoy()
    if any("MÁXIMO" in e["impacto"] for e in hoy):
        return "🚨 ALERTA MÁXIMA — Evento de máximo impacto hoy. Reduce tamaño o no operes.", "#ff4444"
    elif any("🔴 ALTO" in e["impacto"] for e in hoy):
        return "⚠️ PRECAUCIÓN — Datos de alto impacto hoy. Ajusta stops antes del dato.", "#ff8800"
    return "✅ DÍA TRANQUILO — Sin eventos de alto impacto. Condiciones normales.", "#00aa55"


def obtener_noticias():
    noticias = []
    fuentes = [
        ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=EURUSD=X&region=US&lang=en-US", "Yahoo Finance"),
        ("https://www.forexlive.com/feed/news", "ForexLive"),
    ]
    try:
        import ssl as _ssl
        for url, fuente in fuentes:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8, context=_ssl.create_default_context()) as r:
                contenido = r.read().decode("utf-8", errors="ignore")
            items = re.findall(r"<item>(.*?)</item>", contenido, re.DOTALL)
            for item in items[:4]:
                titulo_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", item)
                link_m   = re.search(r"<link>(.*?)</link>|<guid[^>]*>(https?://.*?)</guid>", item)
                if titulo_m:
                    titulo = (titulo_m.group(1) or titulo_m.group(2) or "").strip()
                    link   = (link_m.group(1) or link_m.group(2) or "").strip() if link_m else ""
                    if titulo and len(titulo) > 15:
                        noticias.append({"titulo": titulo, "link": link, "fuente": fuente})
            if len(noticias) >= 5:
                break
    except:
        pass
    if not noticias:
        noticias = [
            {"titulo": "FXStreet — Noticias Forex en vivo", "link": "https://www.fxstreet.com", "fuente": "FXStreet"},
            {"titulo": "ForexLive — Análisis y noticias", "link": "https://www.forexlive.com", "fuente": "ForexLive"},
            {"titulo": "Investing.com — Calendario económico", "link": "https://www.investing.com/economic-calendar/", "fuente": "Investing"},
        ]
    return noticias


def construir_html(resultados):
    ahora = datetime.now().strftime("%A %d de %B, %Y — %H:%M hrs")
    alerta_txt, alerta_color = nivel_alerta()
    hoy_eventos = evento_hoy()
    noticias = obtener_noticias()

    # Tabla de pares
    filas_pares = ""
    filas_setup = ""
    for par, ind in resultados.items():
        if not ind:
            continue
        sr = SOPORTES_RESISTENCIAS.get(par, {})
        razones_html = "<br>".join(ind["razones"])
        filas_pares += f"""
        <tr>
          <td style="font-weight:bold;padding:8px;border-bottom:1px solid #333;">{par}</td>
          <td style="padding:8px;border-bottom:1px solid #333;color:#fff;">{ind['precio']}</td>
          <td style="padding:8px;border-bottom:1px solid #333;color:#aaa;font-size:11px;">RSI: {ind['rsi']}<br>EMA20: {ind['ema20']}<br>EMA50: {ind['ema50']}</td>
          <td style="padding:8px;border-bottom:1px solid #333;color:#00cc88;font-size:11px;">{" | ".join(sr.get('s',[]))}</td>
          <td style="padding:8px;border-bottom:1px solid #333;color:#ff6666;font-size:11px;">{" | ".join(sr.get('r',[]))}</td>
          <td style="padding:8px;border-bottom:1px solid #333;font-size:11px;color:#ccc;">{razones_html}</td>
          <td style="padding:8px;border-bottom:1px solid #333;font-weight:bold;color:{ind['color']};">{ind['sesgo']}</td>
        </tr>"""

        setup = calcular_setup(par, ind)
        if setup:
            filas_setup += f"""
            <tr>
              <td style="font-weight:bold;padding:8px;border-bottom:1px solid #333;">{par}</td>
              <td style="padding:8px;border-bottom:1px solid #333;font-weight:bold;color:{ind['color']};">{setup['direccion']}</td>
              <td style="padding:8px;border-bottom:1px solid #333;color:#fff;">{setup['entrada']}</td>
              <td style="padding:8px;border-bottom:1px solid #333;color:#ff6666;">{setup['sl']}</td>
              <td style="padding:8px;border-bottom:1px solid #333;color:#00cc88;">{setup['tp']}</td>
              <td style="padding:8px;border-bottom:1px solid #333;color:#aaa;">{setup['tf']}</td>
            </tr>"""

    # Eventos hoy
    if hoy_eventos:
        filas_hoy = "".join(f"""
        <tr><td style="padding:6px;border-bottom:1px solid #333;">{e['hora']}</td>
        <td style="padding:6px;border-bottom:1px solid #333;font-weight:bold;">{e['evento']}</td>
        <td style="padding:6px;border-bottom:1px solid #333;">{e['impacto']}</td>
        <td style="padding:6px;border-bottom:1px solid #333;">{e['par']}</td></tr>"""
        for e in hoy_eventos)
        tabla_hoy = f'<table width="100%" style="border-collapse:collapse;font-size:13px;"><tr style="background:#1a1a2e;color:#aaa;"><th style="padding:6px;text-align:left;">Hora</th><th style="padding:6px;text-align:left;">Evento</th><th style="padding:6px;text-align:left;">Impacto</th><th style="padding:6px;text-align:left;">Par</th></tr>{filas_hoy}</table>'
    else:
        tabla_hoy = "<p style='color:#aaa;'>Sin eventos de alto impacto hoy ✅</p>"

    noticias_html = "".join(
        f"<p style='margin:6px 0;font-size:13px;'>"
        f"• <a href='{n[\"link\"]}' style='color:#7ecfff;text-decoration:none;' target='_blank'>{n['titulo']}</a>"
        f" <span style='color:#555;font-size:11px;'>({n['fuente']})</span></p>"
        if n.get("link") else
        f"<p style='margin:6px 0;font-size:13px;color:#ccc;'>• {n['titulo']}</p>"
        for n in noticias
    )

    filas_semana = "".join(f"""
    <tr style="background:{'#2a0000' if 'MÁXIMO' in e['impacto'] else '#1a1a1a'};">
      <td style="padding:6px;border-bottom:1px solid #2a2a2a;">{e['dia']}</td>
      <td style="padding:6px;border-bottom:1px solid #2a2a2a;">{e['hora']}</td>
      <td style="padding:6px;border-bottom:1px solid #2a2a2a;font-weight:bold;">{e['evento']}</td>
      <td style="padding:6px;border-bottom:1px solid #2a2a2a;">{e['impacto']}</td>
    </tr>""" for e in EVENTOS_SEMANA)

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0d0d0d;font-family:Arial,sans-serif;color:#e0e0e0;">
<table width="100%" style="max-width:720px;margin:0 auto;background:#111;border-radius:10px;overflow:hidden;">

<tr><td style="background:linear-gradient(135deg,#0f3460,#16213e);padding:24px 28px;">
  <h1 style="margin:0;font-size:22px;color:#00d4ff;">📊 FOREX DASHBOARD — DATOS EN VIVO</h1>
  <p style="margin:6px 0 0;color:#7ecfff;font-size:13px;">{ahora} — Santiago, Chile</p>
</td></tr>

<tr><td style="padding:16px 28px;background:{alerta_color}22;border-left:4px solid {alerta_color};">
  <p style="margin:0;font-size:14px;font-weight:bold;color:{alerta_color};">{alerta_txt}</p>
</td></tr>

<tr><td style="padding:20px 28px;">
  <h2 style="margin:0 0 10px;font-size:15px;color:#00d4ff;border-bottom:1px solid #222;padding-bottom:6px;">🌍 CONTEXTO MACRO</h2>
  <div style="font-size:13px;line-height:1.8;color:#ccc;white-space:pre-line;">{CONTEXTO_MACRO}</div>
</td></tr>

<tr><td style="padding:0 28px 20px;">
  <h2 style="margin:0 0 10px;font-size:15px;color:#00d4ff;border-bottom:1px solid #222;padding-bottom:6px;">📰 NOTICIAS FOREX</h2>
  {noticias_html}
</td></tr>

<tr><td style="padding:0 28px 20px;">
  <h2 style="margin:0 0 10px;font-size:15px;color:#ffcc00;border-bottom:1px solid #222;padding-bottom:6px;">⚡ EVENTOS HOY</h2>
  {tabla_hoy}
</td></tr>

<tr><td style="padding:0 28px 20px;">
  <h2 style="margin:0 0 10px;font-size:15px;color:#00d4ff;border-bottom:1px solid #222;padding-bottom:6px;">📈 ANÁLISIS TÉCNICO EN VIVO</h2>
  <table width="100%" style="border-collapse:collapse;font-size:12px;">
    <tr style="background:#1a1a2e;color:#aaa;">
      <th style="padding:8px;text-align:left;">Par</th>
      <th style="padding:8px;text-align:left;">Precio</th>
      <th style="padding:8px;text-align:left;">Indicadores</th>
      <th style="padding:8px;text-align:left;">🟢 Soporte</th>
      <th style="padding:8px;text-align:left;">🔴 Resistencia</th>
      <th style="padding:8px;text-align:left;">Señales</th>
      <th style="padding:8px;text-align:left;">Sesgo</th>
    </tr>
    {filas_pares}
  </table>
</td></tr>

<tr><td style="padding:0 28px 20px;">
  <h2 style="margin:0 0 10px;font-size:15px;color:#00ff88;border-bottom:1px solid #222;padding-bottom:6px;">🎯 SETUPS DE TRADING HOY</h2>
  <table width="100%" style="border-collapse:collapse;font-size:13px;">
    <tr style="background:#1a1a2e;color:#aaa;">
      <th style="padding:8px;text-align:left;">Par</th>
      <th style="padding:8px;text-align:left;">Dirección</th>
      <th style="padding:8px;text-align:left;">Entrada</th>
      <th style="padding:8px;text-align:left;">Stop Loss</th>
      <th style="padding:8px;text-align:left;">Take Profit</th>
      <th style="padding:8px;text-align:left;">Timeframe</th>
    </tr>
    {filas_setup if filas_setup else '<tr><td colspan="6" style="padding:12px;color:#aaa;text-align:center;">⚠️ Sin setups claros hoy — esperar mejores condiciones</td></tr>'}
  </table>
</td></tr>

<tr><td style="padding:0 28px 20px;">
  <h2 style="margin:0 0 10px;font-size:15px;color:#00d4ff;border-bottom:1px solid #222;padding-bottom:6px;">📅 CALENDARIO SEMANAL</h2>
  <table width="100%" style="border-collapse:collapse;font-size:12px;">
    <tr style="background:#1a1a2e;color:#aaa;">
      <th style="padding:6px;text-align:left;">Día</th>
      <th style="padding:6px;text-align:left;">Hora</th>
      <th style="padding:6px;text-align:left;">Evento</th>
      <th style="padding:6px;text-align:left;">Impacto</th>
    </tr>
    {filas_semana}
  </table>
</td></tr>

<tr><td style="padding:16px 28px;background:#0f3460;border-top:1px solid #1a3a6e;">
  <p style="margin:0;font-size:13px;color:#aaccff;line-height:1.6;">
    💬 <strong style="color:#fff;">¿Qué hacer?</strong> Abre Claude en tu celular y escribe:<br>
    <strong style="color:#00d4ff;">"Claude, llegó mi dashboard. Dame el análisis y setup de hoy."</strong>
  </p>
</td></tr>

<tr><td style="padding:12px 28px;background:#0a0a0a;text-align:center;">
  <p style="margin:0;font-size:11px;color:#444;">Forex Dashboard — Felipe Mejía • Datos: Yahoo Finance • No es asesoría financiera</p>
</td></tr>

</table></body></html>"""


def enviar_correo():
    if not GMAIL_PASSWORD:
        print("❌ ERROR: Contraseña de Gmail no configurada.")
        return False

    print("📡 Obteniendo datos en vivo...")
    resultados = {}
    for par, simbolo in PARES.items():
        resultados[par] = calcular_indicadores(simbolo)
        print(f"  ✅ {par} obtenido")

    hoy = datetime.now()
    asunto = f"📊 Forex Dashboard — {hoy.strftime('%A %d %b')} | Señales en vivo"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = DESTINATARIO
    msg.attach(MIMEText(construir_html(resultados), "html"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
            server.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, DESTINATARIO, msg.as_string())
        print(f"✅ Correo enviado a {DESTINATARIO}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print(f"  FOREX DASHBOARD — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 50)
    enviar_correo()
