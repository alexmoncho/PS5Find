"""Filtros de anuncios: modelo válido, precio, estado, entrega/pago y señales de estafa.

Cada anuncio es un dict normalizado:
  fuente, id, titulo, descripcion, precio (float, EUR), url,
  envio (bool: la plataforma ofrece envío con pago protegido),
  distancia_km (float o None), estado (str o None: nuevo/como_nuevo/bueno/aceptable/malo),
  tienda (bool: vendedor profesional con garantía, p. ej. CeX)
"""
import re
import unicodedata


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texto.lower()).strip()


# --- Modelo -----------------------------------------------------------------
PS5 = re.compile(r"\b(ps ?5|play ?station ?5|play ?5|playstation5)\b")
XBOX_SERIES = re.compile(r"\bxbox( one)? series ?(x|s)\b|\bseries ?(x|s)\b")

# Cosas que no son una consola capaz de correr GTA VI
NO_CONSOLA = re.compile(
    r"\b(ps ?4|playstation ?4|xbox one(?! series)|ps ?vita|portal|playstation portal|"
    r"ps3|xbox 360|switch)\b"
)

# Accesorios: si el título empieza por uno de estos, o lo menciona y no dice "consola",
# es la venta de un accesorio y no de la consola.
ACCESORIO = (
    r"(mando|mandos|dualsense|dual sense|controller|control|funda|fundas|soporte|base de carga|"
    r"estacion de carga|cargador|juego|juegos|cascos|auriculares|headset|disco duro|ssd|lector|"
    r"unidad de disco|tapa|tapas|carcasa|carcasas|skin|vinilo|ventilador|cable|caja|volante|"
    r"camara|mando edge|edge|pulse|media remote|mando a distancia|codigo|tarjeta|psn|game pass)"
)
EMPIEZA_ACCESORIO = re.compile(rf"^(solo |se vende |vendo |pack de )?{ACCESORIO}\b")

# --- Averías ----------------------------------------------------------------
AVERIA = re.compile(
    r"averiad|no funciona|no enciende|no arranca|para piezas|piezas|despiece|reparar|"
    r"no lee|no da imagen|sin imagen|hdmi roto|hdmi danado|puerto hdmi|luz azul|"
    r"pantalla negra|se apaga|sobrecalienta|bloquead|baneada|baneo|sin probar|"
    r"rota\b|roto\b|golpe|caida|humedad|mojad|defectuos|fallo|falla|tal cual|"
    r"\berror\b|placa base"
)

# --- Estafas ----------------------------------------------------------------
ESTAFA = re.compile(
    r"foto de la caja|solo la caja|solo caja|caja vacia|es una foto|se vende la foto|"
    r"vendo la foto|imagen de la consola|no es la consola|leer bien|leer descripcion|"
    r"lee bien|lee la descripcion|leed bien|"
    r"whatsapp|whats app|wasap|telegram|"
    r"transferencia|pago por adelantado|pago adelantado|western union|paypal amigos|"
    r"amigos y familiares|solo bizum|bizum antes|"
    r"escribeme al|contacta(me)? por email|@gmail|@hotmail|"
    r"precintad[ao] sin abrir.*(envio|enviar) desde (italia|francia|portugal|reino unido|alemania)|"
    r"estoy fuera de espana|me encuentro fuera"
)
TELEFONO = re.compile(r"\b[67]\d{2}[ .-]?\d{3}[ .-]?\d{3}\b")

ESTADOS_OK = {"nuevo", "como_nuevo", "bueno", None}
ESTADO_MALO_TEXTO = re.compile(
    r"muy usad|bastante usad|desgastad|aranazos profundos|con marcas fuertes|estado regular|"
    r"estado aceptable|para reparar|le falta|sin mando y sin cables"
)


# Palabras que pueden ir antes del nombre de la consola en un título legítimo
# ("Vendo consola Sony PS5"). Si antes aparece otra cosa ("Doom ... PS5",
# "Patinete, se cambia por PS5"), el anuncio no es la venta de la consola.
PREFIJO_OK = {
    "vendo", "se", "vende", "mi", "una", "la", "el", "consola", "sony", "microsoft", "nueva", "nuevo",
    "seminueva", "seminuevo", "como", "precintada", "precintado", "oferta", "urge", "urgente",
    "ganga", "chollo", "pack", "playstation", "play", "station", "xbox", "one", "videoconsola",
}


def modelo(anuncio) -> str | None:
    t = normalizar(anuncio["titulo"])
    if re.search(r"\bportal\b|\bcambio\b|\bcambia\b|\bintercambio\b|\bpermuto\b", t):
        return None
    if NO_CONSOLA.search(t) and not (PS5.search(t) or XBOX_SERIES.search(t)):
        return None
    m = PS5.search(t) or XBOX_SERIES.search(t)
    if not m:
        return None
    antes = re.findall(r"[a-z0-9]+", t[: m.start()])
    if any(w not in PREFIJO_OK for w in antes):
        return None
    return "PS5" if PS5.search(t) else "Xbox Series"


CONSOLA_TOKEN = r"(ps ?5|play ?station ?5|play ?5|xbox( one)? series ?(x|s)?|series ?(x|s))"
ACCESORIO_DE_CONSOLA = re.compile(rf"{ACCESORIO}( \w+)?( de| para| compatible con)?( la| una)? {CONSOLA_TOKEN}\b")
PARA_CONSOLA = re.compile(rf"\b(para|compatible con)( la| una)? {CONSOLA_TOKEN}\b")
INCLUSION = re.compile(r"(\+|\bcon|\by|\bincluye|\bmas|,)\s*(\d+|dos|tres|un|una|su|sus)?\s*$")


def es_accesorio(titulo: str) -> bool:
    t = normalizar(titulo)
    tiene_consola = re.search(r"\bconsola\b", t)
    if EMPIEZA_ACCESORIO.search(t) and not tiene_consola:
        return True
    if PARA_CONSOLA.search(t) and not tiene_consola:
        return True
    for m in ACCESORIO_DE_CONSOLA.finditer(t):
        antes = t[: m.start()]
        # "PS5 con mando" o "PS5 + juego" es consola; "mando ps5" no.
        if not INCLUSION.search(antes) and not re.search(CONSOLA_TOKEN, antes) and not tiene_consola:
            return True
    return False


NEGACIONES = re.compile(
    r"\b(sin|ni|nunca ha tenido|no tiene|no ha tenido|cero|ningun tipo de)\s+(ningun |ninguna |un |una |nada de |tipo de )?"
    r"(golpes?|fallos?|errores?|caidas?|problemas?|humedad|defectos?|aranazos|rayas|marcas|averias?|reparaciones?|"
    r"bloqueos?|baneos?)\b"
)


def evaluar(anuncio, cfg) -> tuple[bool, str]:
    """Devuelve (aceptado, motivo)."""
    titulo = normalizar(anuncio["titulo"])
    texto = NEGACIONES.sub(" ", titulo + " " + normalizar(anuncio.get("descripcion", "")))

    m = modelo(anuncio)
    if not m:
        return False, "no es PS5 ni Xbox Series"
    if es_accesorio(anuncio["titulo"]):
        return False, "accesorio o solo mando"

    precio = anuncio.get("precio")
    if precio is None:
        return False, "sin precio"
    if precio > cfg["precio_max"]:
        return False, f"precio {precio:.0f} > {cfg['precio_max']}"
    if precio < cfg["precio_min"]:
        return False, f"precio {precio:.0f} sospechosamente bajo"

    if AVERIA.search(texto):
        return False, "averiada o sin probar"
    if ESTAFA.search(texto) or (not anuncio.get("tienda") and TELEFONO.search(texto)):
        return False, "señales de estafa o pago fuera de la plataforma"

    if anuncio.get("estado") not in ESTADOS_OK or ESTADO_MALO_TEXTO.search(texto):
        return False, "estado peor que bueno"

    # Entrega: en mano en Madrid o envío con pago protegido de la plataforma.
    if anuncio.get("tienda"):
        pass
    else:
        d = anuncio.get("distancia_km")
        en_madrid = d is not None and d <= cfg["madrid"]["radio_km"]
        if not (en_madrid or anuncio.get("envio")):
            return False, "fuera de Madrid y sin envío protegido"

    return True, m
