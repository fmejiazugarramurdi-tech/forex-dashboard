"""Construcción y envío de la alerta por correo."""

import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from config import GMAIL_ADDRESS, GMAIL_PASSWORD, DESTINATARIO, DRY_RUN


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
            "<td style='padding:12px;color:#88aaff;font-weight:bold;'>H1</td>"
            "<td style='padding:12px;font-weight:bold;color:" + color + ";font-size:16px;'>" + op["setup"]["dir"] + "</td>"
            "<td style='padding:12px;color:#fff;'>" + str(op["setup"]["entrada"]) + "</td>"
            "<td style='padding:12px;color:#ff6666;'>" + str(op["setup"]["sl"]) + "</td>"
            "<td style='padding:12px;color:#00cc88;'>" + str(op["setup"]["tp"]) + "</td>"
            "<td style='padding:12px;color:#ffcc00;'>" + str(op["setup"]["ratio"]) + ":1</td>"
            "<td style='padding:12px;color:#aaa;font-size:12px;'>" + tam + "</td>"
            "</tr>"
            "<tr style='background:#1a1a1a;'>"
            "<td colspan='8' style='padding:10px 12px;'>"
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
        "<th style='padding:10px;text-align:left;'>Timeframe</th>"
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


def resumen_texto(oportunidades):
    """Versión en texto plano de la alerta, para el modo DRY_RUN (se ve en el log)."""
    out = []
    for op in oportunidades:
        s = op["setup"]
        out.append(
            op["par"] + " | TF H1 | " + s["dir"] + " | entrada " + str(s["entrada"])
            + " | SL " + str(s["sl"]) + " | TP " + str(s["tp"])
            + " | ratio " + str(s["ratio"]) + ":1 | " + str(op["score"]) + "/5 filtros"
        )
        out.extend("    " + f for f in op["filtros"])
    return "\n".join(out)


def enviar_alerta(oportunidades):
    pares_str = ", ".join(op["par"] for op in oportunidades)
    asunto = "🚨 ALERTA FOREX — " + str(len(oportunidades)) + " oportunidad(es): " + pares_str

    if DRY_RUN:
        print("🧪 DRY_RUN activo — NO se envía correo. Esto se habría enviado:")
        print("Asunto: " + asunto)
        print(resumen_texto(oportunidades))
        return

    if not GMAIL_PASSWORD:
        print("❌ Contraseña no configurada.")
        return

    ahora = datetime.utcnow()

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
