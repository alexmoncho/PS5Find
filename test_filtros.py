"""Pruebas de los filtros con anuncios de ejemplo (escritos a mano, no reales)."""
import json
import unittest
from pathlib import Path

from filtros import evaluar

CFG = json.loads((Path(__file__).parent / "config.json").read_text())


def a(titulo, precio=350, desc="", envio=True, dist=None, estado="bueno", tienda=False, pais="ES"):
    return dict(fuente="t", id="1", titulo=titulo, descripcion=desc, precio=precio, url="",
                envio=envio, distancia_km=dist, estado=estado, tienda=tienda, pais=pais)


ACEPTADOS = [
    a("PS5 Slim 1TB con lector", 450),
    a("Playstation 5 digital + 2 mandos", 400),
    a("PS5 con caja y ticket", 410),                     # edición sin especificar: máx. 420
    a("Consola PS5 Pro", 700),
    a("PS5 Pro 2TB", 650),
    a("Xbox Series X 1TB", 440, desc="Funciona perfectamente, sin ningún golpe ni fallo."),
    a("Xbox Series S 512GB", 180, envio=False, dist=12),
    a("Play 5 con mando y juego", 340),
    a("PS5 Slim", 455, desc="Versión con lector de discos. Envío por Wallapop."),
    a("Vendo consola Sony PS5 Slim digital", 390),
    a("Consola Xbox Series S Blanca", 250),
]

RECHAZADOS = [
    (a("Mando PS5 DualSense blanco", 45), "mando"),
    (a("DualSense Edge para PS5", 160), "mando caro"),
    (a("Funda para PS5 Slim", 20), "funda"),
    (a("Soporte vertical PS5", 15), "soporte"),
    (a("PS4 Pro 1TB", 200), "ps4"),
    (a("PlayStation Portal", 190), "portal"),
    (a("PS5 averiada no enciende", 180), "averiada"),
    (a("PS5 para piezas", 150), "piezas"),
    (a("PS5 Slim", 250, desc="Error de luz azul, ideal para reparar"), "luz azul"),
    (a("PS5 nueva precintada", 300, desc="LEER BIEN: se vende la foto de la caja"), "foto"),
    (a("PS5 Pro", 600, desc="Contactar por WhatsApp, pago por transferencia"), "pago fuera"),
    (a("PS5 Slim", 300, desc="llámame al 612 345 678"), "teléfono"),
    (a("PS5 Slim", 90), "precio bajo"),
    (a("PS5 Pro 2TB", 260), "Pro sospechosamente barata"),
    (a("PS5 Pro 2TB", 780), "Pro por encima de 750"),
    (a("PS5 digital", 430), "Digital por encima de 420"),
    (a("PS5 Slim con lector", 470), "Estándar por encima de 460"),
    (a("PS5 Slim", 440), "sin especificar: máximo de la Digital"),
    (a("Xbox Series X", 460), "Series X por encima de 450"),
    (a("Xbox Series S 512GB", 300), "Series S por encima de 250"),
    (a("Consola Xbox Series S Blanca", 390), "Series S por encima de 250"),
    (a("PS5 Slim", 300, envio=False, dist=300), "lejos sin envío"),
    (a("PS5 Slim", 300, estado="aceptable"), "estado"),
    (a("Caja vacía PS5", 20), "caja vacía"),
    (a("Juego GTA V PS5", 25), "juego"),
    # Falsos positivos vistos en la primera pasada real (Wallapop, 25/11/2026)
    (a("Doom: The Dark Ages Edición de Coleccionista PS5", 200), "juego"),
    (a("PlayStation Portal (PS5)", 150), "portal"),
    (a("PS Portal PS5", 185), "portal"),
    (a("Patinete Xiaomi 4 o se cambia por PS5", 220), "cambio"),
    (a("iPad 10ª o intercambio posible con Xbox Series S", 280), "cambio"),
    (a("Xbox Series S + 2 controladores", 230, pais="IT"), "Italia (Budrio)"),
]


class TestFiltros(unittest.TestCase):
    def test_version(self):
        from filtros import evaluar as ev
        casos = {"PS5 Pro 2TB": "PS5 Pro", "PS5 digital": "PS5 Digital", "PS5 Slim con lector": "PS5 Estándar",
                 "PS5 Slim": "PS5", "Xbox Series X 1TB": "Xbox Series X", "Xbox Series S": "Xbox Series S"}
        for t, esperado in casos.items():
            self.assertEqual(ev(a(t, 200 if "Series S" in t else 400), CFG)[1], esperado, t)

    def test_aceptados(self):
        for x in ACEPTADOS:
            ok, motivo = evaluar(x, CFG)
            self.assertTrue(ok, f"{x['titulo']!r} rechazado: {motivo}")

    def test_rechazados(self):
        for x, por in RECHAZADOS:
            ok, motivo = evaluar(x, CFG)
            self.assertFalse(ok, f"{x['titulo']!r} ({por}) aceptado")


if __name__ == "__main__":
    unittest.main()
