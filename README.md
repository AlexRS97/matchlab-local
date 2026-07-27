# MatchLab — Football Analytics Platform

Plataforma local de análisis probabilístico de fútbol preparada para evolucionar a web y móvil.
Recupera los partidos de una fecha, construye histórico sin duplicarlo y estima goles, córners,
resultado, over 2.5, ambos marcan y marcadores probables. Cada análisis incluye calidad de datos y
confianza: no presenta una predicción como certeza.

## Qué está incluido

- API REST con FastAPI y documentación OpenAPI.
- PostgreSQL, migraciones Alembic y almacenamiento de respuestas RAW.
- API-Football v3 detrás de una interfaz desacoplada.
- Ingesta mundial incremental con Celery y Redis, iniciada manualmente para no consumir recursos
  ni cuota mientras juegas.
- Histórico reciente, standings y estadísticas de córners por equipo.
- Baseline regularizado de Poisson para goles y binomial negativa para córners.
- Snapshots point-in-time de features y predicciones versionadas.
- Web Next.js responsive con cartelera diaria y análisis detallado.
- Proyecto dbt con staging, forma rolling y mart diario.
- Modo demo, pruebas unitarias, Docker Compose y scripts para Windows.
- Captura de cuotas, detección separada de valor esperado y tendencias, rendimiento y calidad.
- Filtros por continente y calidad; prioridad para grandes ligas y torneos internacionales sin
  ocultar el resto de la cartelera.

La autenticación, pagos, app móvil y modelos ML avanzados pertenecen a una fase posterior: requieren
usuarios reales, decisiones de producto y suficiente histórico validado. La arquitectura y la API ya
permiten añadirlos sin reescribir el núcleo.

## Requisito único en tu PC

Instala **Docker Desktop para Windows**, WSL 2 y activa la virtualización AMD-V/SVM o Intel VT-x en
la UEFI/BIOS. No necesitas instalar Python, Node, PostgreSQL ni Redis por separado porque los
contenedores ya los incluyen.

Puedes comprobar todos los requisitos antes de arrancar:

```powershell
.\scripts\doctor.ps1
```

En placas ASUS con procesador AMD, la virtualización suele estar en `F7 > Advanced >
CPU Configuration > SVM Mode > Enabled`. Guarda los cambios con `F10`.

## Arranque rápido

La forma recomendada de usar MatchLab en Windows es el acceso directo del escritorio. Para instalarlo
o repararlo:

```powershell
.\scripts\install-desktop.ps1
```

Al abrir **MatchLab** aparece su icono en la zona de iconos ocultos de la barra de tareas. Desde su
menú puedes abrir la web, actualizar los datos, reactivar los servicios o seleccionar **Detener para
jugar**. Esta última opción detiene los contenedores y Docker Desktop sin borrar la base de datos.
Al volver a abrir el acceso directo, todo arranca de nuevo automáticamente.

También puedes iniciarlo manualmente. Abre PowerShell en esta carpeta y ejecuta:

```powershell
.\scripts\start.ps1
```

La primera ejecución crea `.env`, construye los servicios, aplica las migraciones y arranca:

- Web: <http://localhost:3000>
- API y documentación interactiva: <http://localhost:8000/docs>
- PostgreSQL y Redis: accesibles únicamente dentro de Docker por seguridad.

Sin clave se abre automáticamente en modo demo con tres partidos y 45 jornadas de histórico simulado.

## Activar datos reales

1. Crea una cuenta en el [panel oficial de API-Football](https://dashboard.api-football.com/).
2. Abre `.env` y pega la clave únicamente en esta variable:

```dotenv
API_FOOTBALL_KEY=tu_clave_real
APP_DEMO_MODE=false
```

3. Reinicia los servicios:

```powershell
.\scripts\stop.ps1
.\scripts\start.ps1 -NoBuild
```

4. En la web pulsa **Actualizar datos**, o ejecuta una ingesta explícita:

```powershell
docker compose exec api python -m football_api.cli ingest --date 2026-07-17
```

La clave queda excluida de Git mediante `.gitignore`. No la compartas ni la introduzcas en el
frontend.

## Flujo de datos

La ingesta consulta primero `/fixtures?date=...` y conserva todos los partidos que entrega el
proveedor para esa fecha. Después prioriza Champions, Europa League, Conference, Libertadores,
Sudamericana, las cinco grandes ligas y las principales competiciones de Asia y América para
descargar hasta 20 partidos previos por equipo, estadísticas, clasificación y cuotas. Las
competiciones restantes continúan visibles y analizadas con la calidad que permitan sus datos.

El catálogo, los historiales, las clasificaciones y las cuotas tienen caché para no repetir llamadas.
También se respeta la cuota diaria comunicada por API-Football y se reserva un pequeño margen. Los
límites de cada ejecución se controlan en `.env`:

```dotenv
MAX_HISTORY_CALLS_PER_RUN=80
MAX_STATISTICS_CALLS_PER_RUN=120
MAX_ODDS_CALLS_PER_RUN=40
API_FOOTBALL_DAILY_CALL_BUDGET=7000
API_FOOTBALL_QUOTA_RESERVE=5
ENABLE_SCHEDULED_INGESTION=false
```

`ENABLE_SCHEDULED_INGESTION=false` es el valor recomendado para este PC: solo se actualiza al pulsar
el botón y nunca arranca con Windows. Las ligas pequeñas y amistosos pueden carecer de córners,
cuotas o clasificación. En esos casos se omite el mercado correspondiente y se reduce la confianza
en lugar de inventar valores. Sin una cuota reciente, una señal se etiqueta como **tendencia**, no
como apuesta de valor.

## Endpoints principales

```text
GET  /api/v1/fixtures?date=YYYY-MM-DD
GET  /api/v1/fixtures/{id}
GET  /api/v1/fixtures/{id}/analysis
GET  /api/v1/daily-analysis?date=YYYY-MM-DD
GET  /api/v1/competitions
GET  /api/v1/teams/{id}/form
GET  /api/v1/value-opportunities?date=YYYY-MM-DD
GET  /api/v1/models/performance
POST /api/v1/admin/ingestion/run?date=YYYY-MM-DD
POST /api/v1/admin/predictions/generate?date=YYYY-MM-DD
GET  /api/v1/admin/jobs
GET  /api/v1/admin/data-quality?date=YYYY-MM-DD
```

## Operaciones habituales

```powershell
# Uso diario ligero
.\scripts\start.ps1 -NoBuild

# Modo juego: detiene MatchLab y Docker Desktop, conservando los datos
.\scripts\stop.ps1 -StopDocker

# Ver logs
docker compose logs -f api worker web

# Ejecutar tests
docker compose run --rm api pytest

# Validación completa
.\scripts\check.ps1

# Ejecutar dbt y sus tests
docker compose --profile analytics run --rm dbt build --profiles-dir .

# Detener sin borrar los datos
.\scripts\stop.ps1

# Borrar también los volúmenes (elimina la base de datos)
docker compose down -v
```

## Interpretación responsable

Un valor de `2.72` significa una media de distribución, no que el partido vaya a tener exactamente
tres goles. La confianza mide cobertura y tamaño de muestra, no probabilidad de acertar una apuesta.
Antes de usar dinero real se necesita un backtest walk-forward, calibración por liga y mercado, cuotas
históricas, closing-line value y una muestra fuera de entrenamiento. Consulta [la arquitectura](docs/architecture.md)
para ver las protecciones ya incorporadas.

## Estructura

```text
apps/api                 FastAPI, Celery, persistencia y servicios
apps/web                 Next.js
packages                 proveedores y modelos estadísticos reutilizables
migrations               Alembic
dbt                      transformaciones y tests analíticos
infrastructure/docker    imágenes de ejecución
scripts                  arranque y comprobaciones para Windows
tests                    pruebas unitarias
docs                     decisiones de arquitectura
```
