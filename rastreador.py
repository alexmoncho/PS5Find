"""Rastreador de consolas para GTA VI.

Uso:
  python rastreador.py              # una pasada: busca, filtra, avisa de lo nuevo
  python rastreador.py --prueba     # envía una notificación de prueba y sale
  python rastreador.py --sin-avisos # busca y guarda sin notificar (útil la primera vez)

Variables de entorno:
  NTFY_TOPIC          tema de ntfy al que estás suscrito en el móvil (secreto del repositorio)
  EBAY_CLIENT_ID      opcional, para activar eBay
  EBAY_CLIENT_SECRET  opcional, para activar eBay
"""
import html
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from filtros import evaluar
from fuentes import FUENTES

RAIZ = Path(__file__).parent
ESTADO = RAIZ / "estado" / "vistos.json"
WEB = RAIZ / "docs" / "index.html"


def avisar(cfg, titulo, cuerpo, url=None, prioridad="high"):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("Sin NTFY_TOPIC: no se envía el aviso ->", titulo)
        return
    h = {"Title": titulo.encode("utf-8"), "Priority": prioridad, "Tags": "video_game"}
    if url:
        h["Click"] = url
    req = urllib.request.Request(f"{cfg['ntfy_servidor']}/{topic}", data=cuerpo.encode("utf-8"), headers=h)
    urllib.request.urlopen(req, timeout=15).read()


def cargar_estado():
    if ESTADO.exists():
        return json.loads(ESTADO.read_text())
    return {"vistos": {}, "activos": []}


def guardar_web(activos):
    filas = "\n".join(
        f"<tr><td>{html.escape(x['fuente'])}</td><td><a href=\"{html.escape(x['url'])}\">"
        f"{html.escape(x['titulo'])}</a></td><td>{x['precio']:.0f} €</td>"
        f"<td>{html.escape(x.get('entrega', ''))}</td><td>{html.escape(x['visto'][:16].replace('T', ' '))}</td></tr>"
        for x in sorted(activos, key=lambda x: x["visto"], reverse=True)
    )
    WEB.parent.mkdir(exist_ok=True)
    WEB.write_text(f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Consolas GTA VI</title>
<style>body{{font-family:system-ui,sans-serif;margin:16px;background:#fff;color:#111}}
table{{border-collapse:collapse;width:100%}}td,th{{padding:6px;border-bottom:1px solid #ddd;text-align:left;font-size:14px}}
@media (prefers-color-scheme:dark){{body{{background:#111;color:#eee}}a{{color:#8bf}}td,th{{border-color:#333}}}}</style>
</head><body><h1>Consolas para GTA VI</h1><p>Anuncios que cumplen los filtros (últimos 7 días).
Actualizado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</p>
<table><tr><th>Portal</th><th>Anuncio</th><th>Precio</th><th>Entrega</th><th>Visto</th></tr>
{filas}</table></body></html>""")


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

    nuevos = []
    for x in candidatos:
        clave = f"{x['fuente']}:{x['id']}:{x['precio'] or 0:.0f}"  # una bajada de precio cuenta como nuevo
        if clave in estado["vistos"]:
            continue
        ok, motivo = evaluar(x, cfg)
        estado["vistos"][clave] = ahora
        if not ok:
            continue
        d = x.get("distancia_km")
        x["entrega"] = ("Tienda con garantía" if x.get("tienda") else
                        f"En mano, {d:.0f} km" if d is not None and d <= cfg["madrid"]["radio_km"] else
                        "Envío protegido")
        x["visto"] = ahora
        x["modelo"] = motivo
        nuevos.append(x)
        estado["activos"].append({k: x[k] for k in ("fuente", "titulo", "precio", "url", "entrega", "visto")})

    print(f"Nuevos que cumplen: {len(nuevos)}")
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
    guardar_web(estado["activos"])


if __name__ == "__main__":
    main()
