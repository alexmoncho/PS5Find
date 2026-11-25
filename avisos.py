"""Envío de avisos: notificaciones push a la web instalada (Web Push) y, opcionalmente, ntfy.

Web Push necesita un par de claves VAPID. Para no tener que guardar una clave privada a mano,
se deriva de un único secreto del repositorio, CLAVE_AVISOS (cualquier texto largo y aleatorio).
La clave pública resultante se publica en docs/vapid.json para que la web pueda suscribirse.

Las suscripciones (lo que copia el botón "Activar avisos" de la web) se leen de:
  - el secreto SUSCRIPCIONES_AVISOS (un objeto JSON o una lista de ellos), y/o
  - el fichero estado/suscripciones.json (lista de objetos JSON).
"""
import base64
import hashlib
import json
import os
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).parent
FICHERO_SUSCRIPCIONES = RAIZ / "estado" / "suscripciones.json"
VAPID_PUBLICA = RAIZ / "docs" / "vapid.json"
# Orden de la curva P-256
N_P256 = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def claves_vapid():
    """Devuelve (privada_raw_b64url, publica_b64url) derivadas de CLAVE_AVISOS, o None."""
    secreto = os.environ.get("CLAVE_AVISOS", "").strip()
    if not secreto:
        return None
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    d = int.from_bytes(hashlib.sha256(("vapid:" + secreto).encode()).digest(), "big") % (N_P256 - 1) + 1
    priv = ec.derive_private_key(d, ec.SECP256R1())
    pub = priv.public_key().public_bytes(serialization.Encoding.X962,
                                         serialization.PublicFormat.UncompressedPoint)
    return _b64url(d.to_bytes(32, "big")), _b64url(pub)


def publicar_clave_publica():
    claves = claves_vapid()
    VAPID_PUBLICA.parent.mkdir(exist_ok=True)
    VAPID_PUBLICA.write_text(json.dumps({"publicKey": claves[1] if claves else None}))


def suscripciones():
    subs = []
    crudo = os.environ.get("SUSCRIPCIONES_AVISOS", "").strip()
    if crudo:
        try:
            v = json.loads(crudo)
            subs += v if isinstance(v, list) else [v]
        except json.JSONDecodeError:
            print("SUSCRIPCIONES_AVISOS no es JSON válido; se ignora")
    if FICHERO_SUSCRIPCIONES.exists():
        subs += json.loads(FICHERO_SUSCRIPCIONES.read_text())
    vistos, unicas = set(), []
    for s in subs:
        if isinstance(s, dict) and s.get("endpoint") and s["endpoint"] not in vistos:
            vistos.add(s["endpoint"])
            unicas.append(s)
    return unicas


def enviar_webpush(titulo, cuerpo, url=None, sesion=None):
    claves = claves_vapid()
    subs = suscripciones()
    if not claves or not subs:
        return 0
    from pywebpush import WebPushException, webpush

    datos = json.dumps({"title": titulo, "body": cuerpo, "url": url or "./"}, ensure_ascii=False)
    enviados = 0
    for s in subs:
        try:
            webpush(subscription_info=s, data=datos, vapid_private_key=claves[0],
                    vapid_claims={"sub": "https://alexmoncho.github.io"},
                    ttl=6 * 3600, requests_session=sesion)
            enviados += 1
        except WebPushException as e:
            codigo = getattr(e.response, "status_code", None)
            if codigo in (404, 410):
                print(f"Suscripción caducada ({codigo}); vuelve a pulsar 'Activar avisos' en la web")
            else:
                print(f"Web Push: error {e!r}")
    return enviados


def enviar_ntfy(servidor, titulo, cuerpo, url=None, prioridad="high"):
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        return False
    h = {"Title": titulo.encode("utf-8"), "Priority": prioridad, "Tags": "video_game"}
    if url:
        h["Click"] = url
    req = urllib.request.Request(f"{servidor}/{topic}", data=cuerpo.encode("utf-8"), headers=h)
    urllib.request.urlopen(req, timeout=15).read()
    return True
