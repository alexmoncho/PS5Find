"""Pruebas de los filtros con anuncios de ejemplo (escritos a mano, no reales)."""
import json
import unittest
from pathlib import Path

from filtros import evaluar

CFG = json.loads((Path(__file__).parent / "config.json").read_text())


def a(titulo, precio=350, desc="", envio=True, dist=None, estado="bueno", tienda=False):
    return dict(fuente="t", id="1", titulo=titulo, descripcion=desc, precio=precio, url="",
                envio=envio, distancia_km=dist, estado=estado, tienda=tienda)


ACEPTADOS = [
    a("PS5 Slim 1TB con lector"),
    a("Playstation 5 digital + 2 mandos", 320),
    a("PS5 con caja y ticket", 380),
    a("Consola PS5 Pro", 399),
    a("Xbox Series X 1TB", 300, desc="Funciona perfectamente, sin ningún golpe ni fallo."),
    a("Xbox Series S 512GB", 180, envio=False, dist=12),
    a("Play 5 con mando y juego", 340),
    a("PS5 estándar", 330, desc="Nunca ha tenido problemas. Envío por Wallapop."),
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
    (a("PS5 nueva precintada", 200, desc="LEER BIEN: se vende la foto de la caja"), "foto"),
    (a("PS5 Pro", 250, desc="Contactar por WhatsApp, pago por transferencia"), "pago fuera"),
    (a("PS5 Slim", 300, desc="llámame al 612 345 678"), "teléfono"),
    (a("PS5 Slim", 90), "precio bajo"),
    (a("PS5 Pro 2TB", 650), "precio alto"),
    (a("PS5 Slim", 300, envio=False, dist=300), "lejos sin envío"),
    (a("PS5 Slim", 300, estado="aceptable"), "estado"),
    (a("Caja vacía PS5", 20), "caja vacía"),
    (a("Juego GTA V PS5", 25), "juego"),
]


class TestFiltros(unittest.TestCase):
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
