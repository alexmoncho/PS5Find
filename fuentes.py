"""Lectura de anuncios por portal. Cada función devuelve una lista de anuncios normalizados
(ver filtros.py). Solo se usan endpoints públicos o API oficiales, con una petición por
búsqueda y ejecución, sin login, sin rotar IP y sin saltarse bloqueos.

AVISO: los endpoints de Wallapop y CeX no son API oficiales documentadas. Son los que usan sus
propias webs y pueden cambiar sin aviso. Si un portal falla, el rastreador lo registra y sigue
con los demás.
"""
import base64
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"


def _get(url, headers=None, data=None, timeout=20):
    h = {"User-Agent": UA, "Accept": "application/json", "Accept-Language": "es-ES,es;q=0.9"}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _distancia_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _pais(loc):
    """'ES' si el anuncio está en España. Usa country_code si Wallapop lo da; si no, por coordenadas."""
    cc = (loc.get("country_code") or "").upper()
    if cc:
        return cc
    lat, lon = loc.get("latitude"), loc.get("longitude")
    if lat is None or lon is None:
        return None
    peninsula_baleares = 35.2 <= lat <= 43.9 and -9.5 <= lon <= 4.6
    canarias = 27.5 <= lat <= 29.5 and -18.3 <= lon <= -13.3
    return "ES" if (peninsula_baleares or canarias) else "XX"


# --- Wallapop ---------------------------------------------------------------
# Endpoint de búsqueda que usa es.wallapop.com. Estado: no verificado desde este entorno.
WALLAPOP_ESTADOS = {
    "new": "nuevo", "as_good_as_new": "como_nuevo", "good": "bueno",
    "fair": "aceptable", "has_given_it_all": "malo",
}


def wallapop(cfg):
    m = cfg["madrid"]
    out = []
    for q in cfg["busquedas"]:
        params = {
            "keywords": q, "source": "search_box", "order_by": "newest",
            "latitude": m["lat"], "longitude": m["lon"],
            "min_sale_price": cfg["precio_min"], "max_sale_price": cfg["precio_max"],
            "category_ids": "12900",  # Consolas y videojuegos
        }
        url = "https://api.wallapop.com/api/v3/search?" + urllib.parse.urlencode(params)
        data = _get(url, {"X-DeviceOS": "0", "Origin": "https://es.wallapop.com",
                          "Referer": "https://es.wallapop.com/"})
        items = (((data.get("data") or {}).get("section") or {}).get("payload") or {}).get("items") \
            or data.get("search_objects") or []
        for it in items:
            if (it.get("reserved") or {}).get("flag"):
                continue
            loc = it.get("location") or {}
            precio = it.get("price")
            precio = precio.get("amount") if isinstance(precio, dict) else precio
            ship = it.get("shipping") or {}
            out.append(dict(
                fuente="Wallapop", id=str(it.get("id")), titulo=it.get("title", ""),
                descripcion=it.get("description", ""), precio=float(precio) if precio is not None else None,
                url=f"https://es.wallapop.com/item/{it.get('web_slug', it.get('id'))}",
                envio=bool(ship.get("item_is_shippable") and ship.get("user_allows_shipping")),
                distancia_km=_distancia_km(m["lat"], m["lon"], loc.get("latitude"), loc.get("longitude")),
                estado=WALLAPOP_ESTADOS.get((it.get("condition") or {}).get("value")
                                            if isinstance(it.get("condition"), dict) else it.get("condition")),
                tienda=False, ciudad=loc.get("city", ""), pais=_pais(loc),
            ))
        time.sleep(3)
    return out


# --- CeX (tienda de segunda mano con garantía; venta online y tiendas en Madrid) -------------
def cex(cfg):
    out = []
    for q in cfg["busquedas"]:
        params = {"q": q, "firstRecord": 1, "count": 50, "sortBy": "relevance", "sortOrder": "desc"}
        url = "https://wss2.cex.es.webuy.io/v3/boxes?" + urllib.parse.urlencode(params)
        data = _get(url)
        boxes = (((data.get("response") or {}).get("data")) or {}).get("boxes") or []
        for b in boxes:
            if b.get("outOfEcomStock") and b.get("outOfStock"):
                continue
            cat = (b.get("categoryFriendlyName") or b.get("categoryName") or "").lower()
            if "consola" not in cat and "console" not in cat:
                continue
            nombre = b.get("boxName", "")
            # CeX gradúa A (como nuevo), B (bueno), C (con marcas). C queda fuera.
            g = re.search(r",\s*([ABC])\s*$", nombre)
            estado = {"A": "como_nuevo", "B": "bueno", "C": "aceptable"}.get(g.group(1) if g else "", "bueno")
            out.append(dict(
                fuente="CeX", id=str(b.get("boxId")), titulo=nombre, descripcion="",
                precio=float(b["sellPrice"]) if b.get("sellPrice") is not None else None,
                url=f"https://es.webuy.com/product-detail?id={b.get('boxId')}",
                envio=True, distancia_km=None, estado=estado, tienda=True, ciudad="",
            ))
        time.sleep(3)
    return out


# --- eBay (API oficial Browse; requiere claves gratuitas de developer.ebay.com) -------------
EBAY_ESTADOS = {"1000": "nuevo", "1500": "nuevo", "2010": "como_nuevo", "2020": "como_nuevo",
                "2030": "bueno", "2500": "como_nuevo", "2750": "como_nuevo", "3000": "bueno",
                "4000": "bueno", "5000": "aceptable", "6000": "aceptable", "7000": "malo"}


def _ebay_token():
    cid, secret = os.environ.get("EBAY_CLIENT_ID"), os.environ.get("EBAY_CLIENT_SECRET")
    if not cid or not secret:
        return None
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials",
                                   "scope": "https://api.ebay.com/oauth/api_scope"}).encode()
    data = _get("https://api.ebay.com/identity/v1/oauth2/token",
                {"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"}, body)
    return data["access_token"]


def ebay(cfg):
    token = _ebay_token()
    if not token:
        print("eBay: sin EBAY_CLIENT_ID/EBAY_CLIENT_SECRET, se omite")
        return []
    out = []
    for q in cfg["busquedas"]:
        filtro = (f"price:[{cfg['precio_min']}..{cfg['precio_max']}],priceCurrency:EUR,"
                  "itemLocationCountry:ES,buyingOptions:{FIXED_PRICE|BEST_OFFER}")
        params = {"q": q, "filter": filtro, "sort": "newlyListed", "limit": 50}
        url = "https://api.ebay.com/buy/browse/v1/item_summary/search?" + urllib.parse.urlencode(params)
        data = _get(url, {"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_ES"})
        for it in data.get("itemSummaries", []):
            out.append(dict(
                fuente="eBay", id=it["itemId"], titulo=it.get("title", ""), descripcion="",
                precio=float(it["price"]["value"]), url=it.get("itemWebUrl", ""),
                envio=True,  # pago dentro de eBay con Garantía al cliente
                distancia_km=None, estado=EBAY_ESTADOS.get(str(it.get("conditionId")), None),
                tienda=False, ciudad=(it.get("itemLocation") or {}).get("city", ""),
            ))
    return out


FUENTES = {"wallapop": wallapop, "cex": cex, "ebay": ebay}
