# Rastreador de consolas para GTA VI

Busca cada 30 minutos PS5 (Digital, Estándar, Pro) y Xbox Series S/X de segunda mano, filtra las que cumplen los requisitos y manda una notificación al móvil con el enlace al anuncio. La web (`docs/`, publicada con GitHub Pages) se instala en la pantalla de inicio como una app, muestra los anuncios válidos de los últimos 7 días y recibe los avisos.

## Filtros

- Modelo: PS5 o Xbox Series. Fuera PS4, Xbox One, PlayStation Portal y accesorios (mandos, fundas, soportes, juegos, cajas).
- Precio máximo por modelo (segunda mano entre particulares); por debajo del primer valor se marca como "buen precio":
  - Xbox Series S: 220–250 €
  - Xbox Series X: 400–450 €
  - PS5 Digital: 380–420 €
  - PS5 Estándar (con lector): 420–460 €
  - PS5 Pro: 650–750 €
  - Si el anuncio no dice la edición de PS5 se aplica el máximo de la Digital; si no dice Series S o X, el de la Series S.
  - Precios anormalmente bajos para el modelo (p. ej. una PS5 Pro por menos de 350 €) se descartan como posible estafa.
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

1. **Repositorio público**: *Settings → General → Danger Zone → Change visibility → Public*. GitHub Pages es gratis solo en repositorios públicos. Las claves de los avisos van en secretos y no se ven.
2. **Web**: *Settings → Pages → Build and deployment → Deploy from a branch*, rama `main`, carpeta `/docs`, *Save*. Queda en https://alexmoncho.github.io/PS5Find/
3. **Clave de los avisos**: *Settings → Secrets and variables → Actions → New repository secret*, nombre `CLAVE_AVISOS`, valor cualquier texto largo inventado (no hace falta recordarlo). Después *Actions → Rastreo de consolas → Run workflow* para que la web reciba la clave pública.
4. **Instalar en el móvil**: abre la web.
   - Android (Chrome): menú ⋮ → *Instalar aplicación* o *Añadir a pantalla de inicio*.
   - iPhone (Safari, iOS 16.4 o superior): *Compartir → Añadir a pantalla de inicio*. En iPhone los avisos solo funcionan abriendo la web desde ese icono.
5. **Activar avisos**: desde la app instalada, pulsa *Activar avisos*, acepta el permiso y pulsa *Copiar código*. Pega ese código como nuevo secreto `SUSCRIPCIONES_AVISOS` (o pásaselo a Claude para que lo añada a `estado/suscripciones.json`).

Desde la siguiente pasada te llega una notificación por cada consola nueva; al tocarla se abre el anuncio. Si cambias `CLAVE_AVISOS` o borras los datos del navegador, repite el paso 5.

Opcional: claves de eBay (developer.ebay.com, claves de producción) como secretos `EBAY_CLIENT_ID` y `EBAY_CLIENT_SECRET`. También puedes recibir los avisos con la app ntfy poniendo el nombre de tu canal en el secreto `NTFY_TOPIC`.
