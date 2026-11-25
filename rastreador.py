"""Rastreador de consolas para GTA VI.

Uso:
  python rastreador.py              # una pasada: busca, filtra, avisa de lo nuevo
  python rastreador.py --prueba     # envía una notificación de prueba y sale
  python rastreador.py --sin-avisos # busca y guarda sin notificar (útil la primera vez)

Variables de entorno (secretos del repositorio):
  CLAVE_AVISOS          texto largo aleatorio del que salen las claves de las notificaciones de la web
  SUSCRIPCIONES_AVISOS  opcional, el código que copia "Activar avisos" (también vale estado/suscripciones.json)
  NTFY_TOPIC            opcional, alternativa con la app ntfy
  EBAY_CLIENT_ID      opcional, para activar eBay
  EBAY_CLIENT_SECRET  opcional, para activar eBay
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import avisos
from filtros import evaluar
from fuentes import FUENTES

RAIZ = Path(__file__).parent
ESTADO = RAIZ / "estado" / "vistos.json"
WEB_DATOS = RAIZ / "docs" / "anuncios.json"


def avisar(cfg, titulo, cuerpo, url=None, prioridad="high"):
    n = avisos.enviar_webpush(titulo, cuerpo, url)
    try:
        ntfy = avisos.enviar_ntfy(cfg["ntfy_servidor"], titulo, cuerpo, url, prioridad)
    except Exception as e:
        print(f"ntfy: error {e!r}")
        ntfy = False
    if not n and not ntfy:
        print("Sin avisos configurados (CLAVE_AVISOS + suscripción, o NTFY_TOPIC) ->", titulo)


def cargar_estado():
    if ESTADO.exists():
        return json.loads(ESTADO.read_text())
    return {"vistos": {}, "activos": []}


def guardar_web(activos, errores):
    """Datos que lee la web (docs/index.html): anuncios activos y hora de la última pasada."""
    WEB_DATOS.parent.mkdir(exist_ok=True)
    WEB_DATOS.write_text(json.dumps({
        "actualizado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "portales_con_error": errores,
        "anuncios": sorted(activos, key=lambda x: x["visto"], reverse=True),
    }, ensure_ascii=False, indent=1))
    avisos.publicar_clave_publica()


def main():
    cfg = json.loads((RAIZ / "config.json").read_text())
    if "--prueba" in sys.argv:
        avisar(cfg, "Prueba del rastreador", "Si ves esto, los avisos funcionan.", prioridad="default")
        return
    sin_avisos = "--sin-avisos" in sys.argv
    estado = cargar_estado()
    primera_vez = not estado["vistos"]
    ahora = datetime.now(timezone.utc).isoformat()

    candidatos, errores = [], []
    for nombre, fn in FUENTES.items():
        if not cfg["fuentes"].get(nombre):
            continue
        try:
            r = fn(cfg)
            print(f"{nombre}: {len(r)} anuncios leídos")
            candidatos += r
        except Exception as e:  # un portal caído no tumba a los demás
            print(f"{nombre}: ERROR {e!r}")
            errores.append(nombre)

    nuevos, motivos = [], {}
    for x in candidatos:
        clave = f"{x['fuente']}:{x['id']}:{x['precio'] or 0:.0f}"  # una bajada de precio cuenta como nuevo
        if clave in estado["vistos"]:
            continue
        ok, motivo = evaluar(x, cfg)
        estado["vistos"][clave] = ahora
        if not ok:
            motivos[motivo] = motivos.get(motivo, 0) + 1
            if motivo not in ("no es PS5 ni Xbox Series", "accesorio o solo mando"):
                print(f"  descartada ({motivo}): {x['precio']} € · {x['titulo'][:60]}")
            continue
        d = x.get("distancia_km")
        x["entrega"] = ("Tienda con garantía" if x.get("tienda") else
                        f"En mano, {d:.0f} km" if d is not None and d <= cfg["madrid"]["radio_km"] else
                        "Envío protegido")
        x["visto"] = ahora
        x["modelo"] = motivo
        nuevos.append(x)
        estado["activos"].append({k: x.get(k, "") for k in ("fuente", "titulo", "precio", "url", "entrega", "visto", "modelo", "ciudad")})

    print(f"Nuevos que cumplen: {len(nuevos)}")
    for m, n in sorted(motivos.items(), key=lambda kv: -kv[1]):
        print(f"  descartados por {m}: {n}")
    if not (sin_avisos or primera_vez):
        for x in nuevos[: cfg["max_avisos_por_ejecucion"]]:
            avisar(cfg, f"{x['modelo']} · {x['precio']:.0f} € · {x['fuente']}",
                   f"{x['titulo']}\n{x['entrega']}{' · ' + x['ciudad'] if x.get('ciudad') else ''}", x["url"])
            time.sleep(1)
    elif primera_vez and nuevos:
        avisar(cfg, "Rastreador activado", f"Hay {len(nuevos)} anuncios que ya cumplen los filtros. "
               "Desde ahora te aviso solo de los nuevos.", prioridad="default")

    # Si un portal falla 3 veces seguidas, avisa una vez.
    fallos = estado.setdefault("fallos", {})
    for n in FUENTES:
        if n in errores:
            fallos[n] = fallos.get(n, 0) + 1
            if fallos[n] == 3:
                avisar(cfg, f"{n} no responde", "El portal lleva 3 pasadas fallando; puede haber "
                       "cambiado o bloqueado el acceso.", prioridad="low")
        else:
            fallos[n] = 0

    # Limpieza: activos de 7 días, vistos de 30.
    limite7, limite30 = time.time() - 7 * 86400, time.time() - 30 * 86400
    ts = lambda s: datetime.fromisoformat(s).timestamp()
    estado["activos"] = [x for x in estado["activos"] if ts(x["visto"]) > limite7]
    estado["vistos"] = {k: v for k, v in estado["vistos"].items() if ts(v) > limite30}

    ESTADO.parent.mkdir(exist_ok=True)
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1))
    guardar_web(estado["activos"], errores)


if __name__ == "__main__":
    main()
