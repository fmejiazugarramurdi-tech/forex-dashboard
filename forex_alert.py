"""
=============================================================
  FOREX ALERT SYSTEM — Felipe Mejía
  Monitorea 10 pares cada hora
  Envía alerta cuando se cumplen 4/5 o 5/5 filtros
  fmejiazugarramurdi@gmail.com
=============================================================
"""

from datetime import datetime

from config import PARES
from indicators import es_horario_seguro, calcular_indicadores
from filters import evaluar_filtros, calcular_setup
from notify import enviar_alerta


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
