"""Prueba de ida y vuelta de los avisos Web Push sin red: cifra como lo haría GitHub Actions
y descifra como lo haría el móvil, y comprueba la firma VAPID con la clave pública publicada."""
import base64
import json
import os
import unittest
from unittest import mock

import http_ece
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

import avisos


def b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def b64e(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class Sesion:
    def __init__(self):
        self.peticiones = []

    def post(self, url, **kw):
        self.peticiones.append((url, kw))
        return mock.Mock(status_code=201, text="", headers={})


class TestAvisos(unittest.TestCase):
    def setUp(self):
        # "Móvil": par de claves del navegador y secreto de autenticación
        self.movil = ec.generate_private_key(ec.SECP256R1())
        pub = self.movil.public_key().public_bytes(serialization.Encoding.X962,
                                                   serialization.PublicFormat.UncompressedPoint)
        self.auth = os.urandom(16)
        self.sub = {"endpoint": "https://push.example/abc", "keys": {"p256dh": b64e(pub), "auth": b64e(self.auth)}}

    def test_sin_configurar_no_envia(self):
        with mock.patch.dict(os.environ, {"CLAVE_AVISOS": "", "SUSCRIPCIONES_AVISOS": ""}):
            self.assertEqual(avisos.enviar_webpush("t", "c"), 0)

    def test_claves_deterministas(self):
        with mock.patch.dict(os.environ, {"CLAVE_AVISOS": "abc"}):
            self.assertEqual(avisos.claves_vapid(), avisos.claves_vapid())
        with mock.patch.dict(os.environ, {"CLAVE_AVISOS": "otra"}):
            otra = avisos.claves_vapid()
        with mock.patch.dict(os.environ, {"CLAVE_AVISOS": "abc"}):
            self.assertNotEqual(avisos.claves_vapid(), otra)

    def test_ida_y_vuelta(self):
        env = {"CLAVE_AVISOS": "una clave de prueba", "SUSCRIPCIONES_AVISOS": json.dumps(self.sub)}
        sesion = Sesion()
        with mock.patch.dict(os.environ, env):
            n = avisos.enviar_webpush("Xbox Series · 300 € · Wallapop", "Xbox Series S Blanca", "https://es.wallapop.com/item/x", sesion)
            publica = avisos.claves_vapid()[1]
        self.assertEqual(n, 1)
        url, kw = sesion.peticiones[0]
        self.assertEqual(url, self.sub["endpoint"])

        # El móvil descifra el contenido
        claro = http_ece.decrypt(kw["data"], private_key=self.movil, auth_secret=self.auth, version="aes128gcm")
        d = json.loads(claro)
        self.assertEqual(d["title"], "Xbox Series · 300 € · Wallapop")
        self.assertEqual(d["url"], "https://es.wallapop.com/item/x")

        # El servicio push valida la firma VAPID con la clave pública que publica la web
        auth = kw["headers"]["Authorization"]
        jwt = auth.split("t=")[1].split(",")[0].strip()
        k = auth.split("k=")[1].strip()
        self.assertEqual(k, publica)
        cab, carga, firma = jwt.split(".")
        sig = b64d(firma)
        der = encode_dss_signature(int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big"))
        clave_pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), b64d(publica))
        clave_pub.verify(der, f"{cab}.{carga}".encode(), ec.ECDSA(hashes.SHA256()))
        self.assertEqual(json.loads(b64d(carga))["aud"], "https://push.example")


if __name__ == "__main__":
    unittest.main()
