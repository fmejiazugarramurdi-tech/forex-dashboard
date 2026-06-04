"""
=============================================================
  FOREX DAILY DASHBOARD — Felipe Mejía
  Envía análisis diario a fmejiazugarramurdi@gmail.com
  Hora programada: 18:30 (Santiago, Chile) — Lunes a Viernes
=============================================================

PRIMERA VEZ: Lee el archivo CONFIGURACION.txt antes de correr esto.
"""

import smtplib
import json
import urllib.request
import urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, date
import ssl
import re

# ─────────────────────────────────────────────
#  CONFIGURACIÓN — EDITA SOLO ESTA SECCIÓN
# ─────────────────────────────────────────────
GMAIL_ADDRESS   = "fmejiazugarramurdi@gmail.com"   # Tu Gmail
GMAIL_APP_PASSWORD = "PEGA_AQUI_TU_CONTRASEÑA_DE_APP"  # Ver CONFIGURACION.txt
DESTINATARIO    = "fmejiazugarramurdi@gmail.com"
# ─────────────────────────────────────────────


PARES = ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "EUR/GBP", "EUR/JPY"]

# Niveles técnicos clave actualizados manualmente cada semana
# (Puedes pedirme a mí — Claude — que los actualice cada lunes)
NIVELES_TECNICOS = {
    "EUR/USD": {
        "soporte":    ["1.1580", "1.1500"],
        "resistencia":["1.1683", "1.1750", "1.1800"],
        "tendencia":  "Lateral-bajista en corto plazo. Canal alcista desde marzo intacto.",
        "sesgo":      "⚠️ NEUTRO — esperar confirmación tras NFP",
        "timeframes": {
            "30min": "⏸️ No operar — esperar NFP",
            "1hr":   "⏸️ No operar — esperar NFP",
            "4hr":   "⏸️ No operar — esperar NFP",
        },
    },
    "GBP/USD": {
        "soporte":    ["1.3400", "1.3300"],
        "resistencia":["1.3500", "1.3600"],
        "tendencia":  "Alcista estructural. Sesgo comprador en pullbacks.",
        "sesgo":      "🟢 ALCISTA — buscar largos en soporte",
        "timeframes": {
            "30min": "🟢 LARGO en 1.3400 — entrada rápida, SL 1.3370",
            "1hr":   "🟢 LARGO en pullback a 1.3400 — SL 1.3360, TP 1.3500",
            "4hr":   "🟢 LARGO en zona 1.3380-1.3400 — SL 1.3300, TP 1.3600",
        },
    },
    "USD/JPY": {
        "soporte":    ["154.00", "152.50"],
        "resistencia":["156.00", "157.50"],
        "tendencia":  "Presión alcista por yields. Vigilar intervención BoJ.",
        "sesgo":      "🟡 ALCISTA CAUTELOSO — atento a yield 10Y USA",
        "timeframes": {
            "30min": "🟡 LARGO solo si supera 155.50 con volumen",
            "1hr":   "🟡 LARGO en soporte 154.00 — SL 153.50, TP 156.00",
            "4hr":   "🟡 LARGO estructural — SL 152.50, TP 157.50",
        },
    },
    "USD/CHF": {
        "soporte":    ["0.8900", "0.8820"],
        "resistencia":["0.9000", "0.9080"],
        "tendencia":  "Bajista en USD. CHF como refugio activo.",
        "sesgo":      "🔴 BAJISTA USD — favorecer cortos en rebotes",
        "timeframes": {
            "30min": "🔴 CORTO en rebote a 0.8970-0.9000 — SL 0.9020",
            "1hr":   "🔴 CORTO en resistencia 0.9000 — SL 0.9040, TP 0.8900",
            "4hr":   "🔴 CORTO en zona 0.9000-0.9080 — SL 0.9100, TP 0.8820",
        },
    },
    "EUR/GBP": {
        "soporte":    ["0.8450", "0.8400"],
        "resistencia":["0.8520", "0.8580"],
        "tendencia":  "Rango estrecho. GBP relativamente fuerte.",
        "sesgo":      "⚠️ NEUTRO — sin tendencia clara",
        "timeframes": {
            "30min": "⏸️ No operar — rango sin dirección clara",
            "1hr":   "⏸️ Esperar ruptura de 0.8520 o caída a 0.8450",
            "4hr":   "⏸️ Rango 0.8400-0.8580 — operar en extremos",
        },
    },
    "EUR/JPY": {
        "soporte":    ["163.00", "161.50"],
        "resistencia":["165.50", "167.00"],
        "tendencia":  "Alcista por carry trade. Sensible a riesgo global.",
        "sesgo":      "🟢 ALCISTA — mantener largos con SL ajustado",
        "timeframes": {
            "30min": "🟢 LARGO en retroceso a 163.50 — SL 163.00",
            "1hr":   "🟢 LARGO en soporte 163.00 — SL 162.50, TP 165.50",
            "4hr":   "🟢 LARGO estructural — SL 161.50, TP 167.00",
        },
    },
}

# Eventos económicos de la semana actual
# (Actualizar cada lunes — o pedirme a mí que los actualice)
EVENTOS_SEMANA = [
    {"dia": "Lunes 2 jun",    "hora": "15:45", "evento": "ISM Manufacturing PMI (EE.UU.)",         "impacto": "🔴 ALTO",    "par": "USD todos"},
    {"dia": "Martes 3 jun",   "hora": "15:45", "evento": "ISM Services PMI (EE.UU.)",              "impacto": "🔴 ALTO",    "par": "USD todos"},
    {"dia": "Miércoles 4 jun","hora": "TBD",   "evento": "Hablan miembros Fed (Warsh/otros)",      "impacto": "🟡 MEDIO",   "par": "USD todos"},
    {"dia": "Jueves 5 jun",   "hora": "09:00", "evento": "PMI Servicios Eurozona",                 "impacto": "🟡 MEDIO",   "par": "EUR/USD"},
    {"dia": "Jueves 5 jun",   "hora": "14:30", "evento": "Jobless Claims EE.UU.",                  "impacto": "🟡 MEDIO",   "par": "USD todos"},
    {"dia": "Viernes 6 jun",  "hora": "14:30", "evento": "⚡ NFP — Nóminas No Agrícolas EE.UU.", "impacto": "🔴🔴 MÁXIMO","par": "TODOS"},
    {"dia": "Viernes 6 jun",  "hora": "14:30", "evento": "Tasa de desempleo EE.UU.",               "impacto": "🔴 ALTO",    "par": "USD todos"},
    {"dia": "Viernes 6 jun",  "hora": "11:00", "evento": "CPI Flash Eurozona",                     "impacto": "🔴 ALTO",    "par": "EUR/USD"},
]

CONTEXTO_MACRO = """
• 💵 DXY (~99.00): Presión bajista estructural. Máximo 2026 fue 99.18 (8 abril). Goldman Sachs proyecta zona 90s en Q4.
• 🏦 FED: Tasa 3.50%-3.75%. Pausa por 3era vez. Nuevo Chair Kevin Warsh: señales dovish = USD negativo.
• 🏦 BCE: Preparando posible subida de tasas en junio = soporte para EUR.
• ⚡ RIESGO GEOPOLÍTICO: Tensiones EE.UU.-Irán elevan petróleo = presión inflacionaria global.
• 📊 PRÓXIMO FOMC: 16-17 junio (primer dot plot bajo Warsh — evento CRUCIAL).
"""


def obtener_noticias_forex():
    """Intenta obtener titulares recientes de forex via RSS público."""
    noticias = []
    fuentes = [
        ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=EURUSD=X&region=US&lang=en-US", "Yahoo Finance"),
        ("https://www.forexlive.com/feed/news", "ForexLive"),
    ]
    for url, fuente in fuentes:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8, context=ssl.create_default_context()) as resp:
                contenido = resp.read().decode("utf-8", errors="ignore")
            titulos = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", contenido)
            for t in titulos[1:6]:
                titulo = (t[0] or t[1]).strip()
                if titulo and len(titulo) > 15:
                    noticias.append(f"• [{fuente}] {titulo}")
        except Exception:
            pass
    if not noticias:
        noticias = [
            "• No se pudieron obtener noticias automáticas hoy.",
            "• Revisa manualmente: fxstreet.com | forexlive.com | investing.com",
        ]
    return noticias


def evento_hoy():
    """Filtra eventos del día actual."""
    hoy = datetime.now()
    dias_es = {0:"Lunes", 1:"Martes", 2:"Miércoles", 3:"Jueves", 4:"Viernes"}
    dia_actual = dias_es.get(hoy.weekday(), "")
    dia_str = f"{dia_actual} {hoy.day}"
    return [e for e in EVENTOS_SEMANA if dia_str.lower() in e["dia"].lower()]


def nivel_alerta_hoy():
    """Determina nivel de alerta según eventos del día."""
    hoy_eventos = evento_hoy()
    maximos = [e for e in hoy_eventos if "MÁXIMO" in e["impacto"]]
    altos   = [e for e in hoy_eventos if "🔴 ALTO" in e["impacto"]]
    if maximos:
        return "🚨 ALERTA MÁXIMA — Evento de máximo impacto hoy. Reduce tamaño de posición o no operes.", "red"
    elif altos:
        return "⚠️ PRECAUCIÓN — Datos de alto impacto hoy. Mueve stops a breakeven antes del dato.", "orange"
    else:
        return "✅ DÍA TRANQUILO — Sin eventos de alto impacto. Condiciones normales para operar.", "green"


def construir_html():
    """Construye el cuerpo del correo en HTML bonito."""
    ahora       = datetime.now().strftime("%A %d de %B, %Y — %H:%M hrs")
    noticias    = obtener_noticias_forex()
    hoy_eventos = evento_hoy()
    alerta_txt, alerta_color = nivel_alerta_hoy()

    colores = {"red": "#ff4444", "orange": "#ff8800", "green": "#00aa55"}
    color_alerta = colores[alerta_color]

    # Tabla de niveles técnicos
    filas_pares = ""
    for par, datos in NIVELES_TECNICOS.items():
        soportes    = " | ".join(datos["soporte"])
        resistencias= " | ".join(datos["resistencia"])
        tf = datos["timeframes"]
        filas_pares += f"""
        <tr>
          <td style="font-weight:bold;padding:8px;border-bottom:1px solid #333;">{par}</td>
          <td style="padding:8px;border-bottom:1px solid #333;color:#00cc88;">{soportes}</td>
          <td style="padding:8px;border-bottom:1px solid #333;color:#ff6666;">{resistencias}</td>
          <td style="padding:8px;border-bottom:1px solid #333;font-size:12px;">{datos['tendencia']}</td>
          <td style="padding:8px;border-bottom:1px solid #333;font-weight:bold;">{datos['sesgo']}</td>
          <td style="padding:8px;border-bottom:1px solid #333;font-size:11px;">
            <span style="color:#aaa;">30m:</span> {tf['30min']}<br>
            <span style="color:#aaa;">1hr:</span> {tf['1hr']}<br>
            <span style="color:#aaa;">4hr:</span> {tf['4hr']}
          </td>
        </tr>"""

    # Tabla de eventos de hoy
    if hoy_eventos:
        filas_hoy = ""
        for e in hoy_eventos:
            filas_hoy += f"""
            <tr>
              <td style="padding:6px;border-bottom:1px solid #333;">{e['hora']}</td>
              <td style="padding:6px;border-bottom:1px solid #333;font-weight:bold;">{e['evento']}</td>
              <td style="padding:6px;border-bottom:1px solid #333;">{e['impacto']}</td>
              <td style="padding:6px;border-bottom:1px solid #333;">{e['par']}</td>
            </tr>"""
        tabla_hoy = f"""
        <table width="100%" style="border-collapse:collapse;font-size:13px;">
          <tr style="background:#1a1a2e;color:#aaa;">
            <th style="padding:6px;text-align:left;">Hora (CL)</th>
            <th style="padding:6px;text-align:left;">Evento</th>
            <th style="padding:6px;text-align:left;">Impacto</th>
            <th style="padding:6px;text-align:left;">Par</th>
          </tr>
          {filas_hoy}
        </table>"""
    else:
        tabla_hoy = "<p style='color:#aaa;'>Sin eventos de alto impacto hoy. ✅</p>"

    # Noticias
    noticias_html = "".join(f"<p style='margin:4px 0;font-size:13px;color:#ccc;'>{n}</p>" for n in noticias)

    # Eventos semana completa
    filas_semana = ""
    for e in EVENTOS_SEMANA:
        bg = "#2a0000" if "MÁXIMO" in e["impacto"] else "#1a1a1a"
        filas_semana += f"""
        <tr style="background:{bg};">
          <td style="padding:6px;border-bottom:1px solid #2a2a2a;">{e['dia']}</td>
          <td style="padding:6px;border-bottom:1px solid #2a2a2a;">{e['hora']}</td>
          <td style="padding:6px;border-bottom:1px solid #2a2a2a;font-weight:bold;">{e['evento']}</td>
          <td style="padding:6px;border-bottom:1px solid #2a2a2a;">{e['impacto']}</td>
          <td style="padding:6px;border-bottom:1px solid #2a2a2a;">{e['par']}</td>
        </tr>"""

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0d0d0d;font-family:Arial,sans-serif;color:#e0e0e0;">

<table width="100%" style="max-width:700px;margin:0 auto;background:#111;border-radius:10px;overflow:hidden;">

  <!-- HEADER -->
  <tr>
    <td style="background:linear-gradient(135deg,#0f3460,#16213e);padding:24px 28px;">
      <h1 style="margin:0;font-size:22px;color:#00d4ff;">📊 FOREX DASHBOARD DIARIO</h1>
      <p style="margin:6px 0 0;color:#7ecfff;font-size:13px;">{ahora} — Santiago, Chile</p>
    </td>
  </tr>

  <!-- ALERTA DEL DÍA -->
  <tr>
    <td style="padding:16px 28px;background:{color_alerta}22;border-left:4px solid {color_alerta};">
      <p style="margin:0;font-size:14px;font-weight:bold;color:{color_alerta};">{alerta_txt}</p>
    </td>
  </tr>

  <!-- CONTEXTO MACRO -->
  <tr>
    <td style="padding:20px 28px;">
      <h2 style="margin:0 0 12px;font-size:15px;color:#00d4ff;border-bottom:1px solid #222;padding-bottom:6px;">
        🌍 CONTEXTO MACROECONÓMICO
      </h2>
      <div style="font-size:13px;line-height:1.7;color:#ccc;white-space:pre-line;">{CONTEXTO_MACRO}</div>
    </td>
  </tr>

  <!-- NOTICIAS -->
  <tr>
    <td style="padding:0 28px 20px;">
      <h2 style="margin:0 0 12px;font-size:15px;color:#00d4ff;border-bottom:1px solid #222;padding-bottom:6px;">
        📰 ÚLTIMAS NOTICIAS FOREX
      </h2>
      {noticias_html}
    </td>
  </tr>

  <!-- EVENTOS HOY -->
  <tr>
    <td style="padding:0 28px 20px;">
      <h2 style="margin:0 0 12px;font-size:15px;color:#ffcc00;border-bottom:1px solid #222;padding-bottom:6px;">
        ⚡ EVENTOS ECONÓMICOS HOY
      </h2>
      {tabla_hoy}
    </td>
  </tr>

  <!-- NIVELES TÉCNICOS -->
  <tr>
    <td style="padding:0 28px 20px;">
      <h2 style="margin:0 0 12px;font-size:15px;color:#00d4ff;border-bottom:1px solid #222;padding-bottom:6px;">
        📈 NIVELES TÉCNICOS CLAVE
      </h2>
      <table width="100%" style="border-collapse:collapse;font-size:13px;">
        <tr style="background:#1a1a2e;color:#aaa;">
          <th style="padding:8px;text-align:left;">Par</th>
          <th style="padding:8px;text-align:left;">🟢 Soporte</th>
          <th style="padding:8px;text-align:left;">🔴 Resistencia</th>
          <th style="padding:8px;text-align:left;">Tendencia</th>
          <th style="padding:8px;text-align:left;">Sesgo</th>
          <th style="padding:8px;text-align:left;">⏱️ Timeframe</th>
        </tr>
        {filas_pares}
      </table>
    </td>
  </tr>

  <!-- EVENTOS SEMANA -->
  <tr>
    <td style="padding:0 28px 20px;">
      <h2 style="margin:0 0 12px;font-size:15px;color:#00d4ff;border-bottom:1px solid #222;padding-bottom:6px;">
        📅 CALENDARIO COMPLETO — ESTA SEMANA
      </h2>
      <table width="100%" style="border-collapse:collapse;font-size:12px;">
        <tr style="background:#1a1a2e;color:#aaa;">
          <th style="padding:6px;text-align:left;">Día</th>
          <th style="padding:6px;text-align:left;">Hora</th>
          <th style="padding:6px;text-align:left;">Evento</th>
          <th style="padding:6px;text-align:left;">Impacto</th>
          <th style="padding:6px;text-align:left;">Par</th>
        </tr>
        {filas_semana}
      </table>
    </td>
  </tr>

  <!-- INSTRUCCIÓN CLAUDE -->
  <tr>
    <td style="padding:16px 28px;background:#0f3460;border-top:1px solid #1a3a6e;">
      <h2 style="margin:0 0 8px;font-size:14px;color:#7ecfff;">💬 ¿QUÉ HACER CON ESTA INFORMACIÓN?</h2>
      <p style="margin:0;font-size:13px;color:#aaccff;line-height:1.6;">
        Abre Claude en tu celular y escribe:<br>
        <strong style="color:#fff;">"Claude, recibí mi dashboard de hoy. Dame el análisis y el mejor setup para operar esta noche."</strong><br><br>
        Claude verá este mismo contexto y te dará entrada, stop loss y take profit en minutos.
      </p>
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="padding:14px 28px;background:#0a0a0a;text-align:center;">
      <p style="margin:0;font-size:11px;color:#444;">
        Script automático • Felipe Mejía Trading Dashboard • No es asesoría financiera
      </p>
    </td>
  </tr>

</table>
</body>
</html>"""
    return html


def enviar_correo():
    if GMAIL_APP_PASSWORD == "PEGA_AQUI_TU_CONTRASEÑA_DE_APP":
        print("❌ ERROR: Debes configurar tu contraseña de app de Gmail.")
        print("   Lee el archivo CONFIGURACION.txt para saber cómo hacerlo.")
        return False

    hoy = datetime.now()
    asunto = f"📊 Forex Dashboard — {hoy.strftime('%A %d %b')} | XTB Trading"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = DESTINATARIO

    html_content = construir_html()
    msg.attach(MIMEText(html_content, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, DESTINATARIO, msg.as_string())
        print(f"✅ Correo enviado exitosamente a {DESTINATARIO}")
        print(f"   Hora: {hoy.strftime('%H:%M:%S')}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ ERROR de autenticación. Revisa tu contraseña de app en CONFIGURACION.txt")
        return False
    except Exception as e:
        print(f"❌ Error al enviar: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("  FOREX DASHBOARD — Felipe Mejía")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 50)
    enviar_correo()
