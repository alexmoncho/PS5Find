# Rastreador de consolas para GTA VI

Busca cada 30 minutos PS5 (Digital, Slim, Pro) y Xbox Series S/X de segunda mano, filtra las que cumplen los requisitos y manda una notificación al móvil con el enlace al anuncio. También genera una página (`docs/index.html`) con los anuncios válidos de los últimos 7 días.

## Filtros

- Modelo: PS5 o Xbox Series. Fuera PS4, Xbox One, PlayStation Portal y accesorios (mandos, fundas, soportes, juegos, cajas).
- Precio: entre 150 y 400 €. Por debajo de 150 casi siempre es avería o estafa.
- Estado: bueno, como nuevo o nuevo. Fuera averiadas, "sin probar", para piezas, luz azul, baneadas.
- Estafas: fuera "foto de la caja", "leer bien", pagos por transferencia/WhatsApp/PayPal amigos, teléfonos en el anuncio.
- Entrega: en mano a menos de 50 km de Madrid, o con envío y pago protegido de la propia plataforma.
- Una bajada de precio se avisa como anuncio nuevo.

Todo se ajusta en `config.json` y `filtros.py`. `python -m unittest test_filtros` comprueba los filtros con anuncios de ejemplo.

## Portales

| Portal | Cómo | Fiabilidad |
|---|---|---|
| Wallapop | Endpoint de búsqueda que usa su web | Media: no es oficial, puede cambiar o bloquear IPs de servidores |
| CeX | Endpoint de catálogo que usa su web | Desactivado: responde 403 desde GitHub (`"cex": true` en `config.json` para reactivarlo) |
| eBay | API oficial Browse | Alta; necesita claves gratuitas |
| Vinted, Milanuncios, Back Market | No incluidos | Tienen anti-bots fuertes; usa sus alertas nativas |

Si un portal falla tres pasadas seguidas, llega un aviso.

## Puesta en marcha

1. Móvil: instala **ntfy** (Play Store / App Store), pulsa "+" y suscríbete a un tema con un nombre largo e imposible de adivinar, por ejemplo `consolas-gta6-<algo-aleatorio>`. Quien conozca el nombre puede leer los avisos.
2. GitHub: crea un repositorio (privado vale), sube esta carpeta y en *Settings → Secrets and variables → Actions* crea el secreto `NTFY_TOPIC` con ese nombre.
3. Opcional, eBay: crea cuenta en developer.ebay.com, genera claves de producción y añade `EBAY_CLIENT_ID` y `EBAY_CLIENT_SECRET` como secretos.
4. Opcional, web: *Settings → Pages*, rama `main`, carpeta `/docs`. En un repo privado Pages requiere plan de pago.
5. *Actions → Rastreo de consolas → Run workflow* para la primera pasada. Esa no avisa de cada anuncio, solo de cuántos hay; desde ahí, solo los nuevos.

