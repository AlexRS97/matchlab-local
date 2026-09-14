# Proveedores

| Fuente | Uso | Configuración |
|---|---|---|
| API-Football | Cartelera, resultados recientes, clasificación, H2H, estadísticas, lesiones, alineaciones y predicción externa | `API_FOOTBALL_KEY` |
| Betfair Exchange oficial | Catálogo, best back y best lay prepartido | Usuario, contraseña, App Key; certificado opcional |
| PulseScore | Bet365 y Winamax; Orbit Exchange como fallback opcional | `PULSESCORE_API_KEY` |
| Football-Data | CSV de resultados y estadísticas para entrenar | Sin clave |
| Manual | Introducir una cuota desde Odds | Sin cuenta adicional |

## API-Football

Crea la cuenta y obtiene la clave en [el panel oficial](https://dashboard.api-football.com/). Usa el acceso directo API-Sports v3, no las credenciales de RapidAPI. Configura el presupuesto con el límite real de tu plan; la plantilla parte de 100 peticiones diarias y reserva 5. La cobertura, temporadas y filtros disponibles dependen de tu cuenta. [Documentación oficial](https://www.api-football.com/documentation-v3).

`API_FOOTBALL_HISTORY_MODE=season` solicita temporadas por equipo, almacena el resultado y reutiliza la respuesta; `last` requiere que tu plan admita ese filtro. Una jornada grande puede superar la cuota gratuita al enriquecer todos los equipos. El backend publica los análisis progresivamente y conserva partidos sin información suficiente.

Los porcentajes 1X2 de `/predictions` se muestran como modelo externo. El consejo Over/Under no se transforma en un porcentaje inventado. xG y xGA solo se usan cuando el proveedor devuelve esos datos. Las estadísticas de prórroga no se tratan como córners de 90 minutos.

## Betfair

Solicita una App Key de desarrollo siguiendo [Getting Started](https://betfair-developer-docs.atlassian.net/wiki/spaces/1smk3cen4v3lu3yomq5qye0ni/pages/2687105/Getting+Started). Configura `BETFAIR_USERNAME`, `BETFAIR_PASSWORD` y `BETFAIR_APP_KEY`. Los campos `BETFAIR_CERT_PATH` y `BETFAIR_KEY_PATH` son opcionales para login con certificado. Las rutas se quedan en el backend; los certificados están ignorados por Git.

Para una cuenta española puede ser necesario `BETFAIR_IDENTITY_DOMAIN=betfair.es`. La disponibilidad depende de tu cuenta y acceso al Exchange. El cliente renueva sesión y conserva el indicador de precio retrasado. Utiliza únicamente `listEvents`, `listMarketCatalogue` y `listMarketBook`; no implementa órdenes.

El precio de ranking es **back**. Lay se conserva por separado. El EV mostrado es bruto y no descuenta la comisión de Exchange. Nunca se confunde Betfair Sportsbook con Exchange.

## PulseScore

Obtén la clave y consulta tus límites en [PulseScore](https://pulsescore.net/docs). Los prefijos de cada casa se configuran en `config/providers.yaml`. Se interpreta su mercado canónico, periodo FULL_TIME, estado activo, línea, lado y marca temporal. No se extrae HTML de bookmakers.

El fallback de Betfair corresponde a **Orbit Exchange (PulseScore)** y conserva esa etiqueta. Está desactivado inicialmente y se puede habilitar en Settings. La prioridad de Betfair es su API oficial mientras exista una cuota fresca.

El presupuesto es mensual y persistente. El intervalo efectivo se amplía según saldo restante y coste del último ciclo, incluidas las páginas. Por eso 500 peticiones al mes no permiten una actualización global cada cinco minutos. Ajusta `PULSESCORE_MONTHLY_BUDGET` a tu plan; la aplicación no compra ni cambia suscripciones.

## Caché y fallos

Cada proveedor tiene caché, contador, límite, reintentos acotados, errores visibles y circuito ante fallos repetidos o HTTP 429. Un fallback a caché conserva la fecha original. Los precios demasiado antiguos quedan fuera del Top; la ausencia de cuota se representa con null. Una selección retirada del último cuadro de precios no sigue vigente solo por existir en el historial.

## Histórico público

Se descargan CSV directos de [Football-Data](https://football-data.co.uk/data.php), con una lista blanca de resultados, córners y tiros. Las columnas de cuotas no entran en el dataset de aprendizaje. Se comprueban diariamente las temporadas actuales; las temporadas antiguas tienen una caché más larga. La publicación de nuevos resultados depende de la fuente y puede ser menos frecuente que la consulta diaria.

Esta fuente alimenta el laboratorio; no reemplaza a API-Football para cargar la cartelera diaria. La validación autenticada de las tres APIs queda pendiente de configurar las credenciales del usuario.

Las importaciones comparan una huella del contenido normalizado: un fichero sin cambios no
reescribe partidos. Cada liga/temporada se reemplaza en una transacción y guarda fecha y revisión.
Las filas duplicadas o una reducción inesperada de partidos se rechazan, conservando la última
versión válida. Una reducción legítima publicada por la fuente requiere revisar esa partición;
no se acepta automáticamente como si fuera una descarga completa.

Model Lab muestra la primera y última fecha disponibles por liga. La fecha de descarga y la del
último resultado son conceptos distintos, especialmente durante parones de competición.
