# Arquitectura

MatchLab es un monolito modular API-first. Los procesos se despliegan por separado, pero comparten
modelos y una base PostgreSQL. Esto reduce la complejidad inicial sin cerrar el camino a separar
servicios cuando exista una necesidad medida.

```text
API-Football
    |
    v
Ingesta Celery ----> raw_api_responses
    |                       |
    v                       v
PostgreSQL <---------- reprocesado
    |
    +--> feature_snapshots --> Poisson / Negative Binomial --> predictions
    |
    +--> dbt staging / intermediate / analytics
    |
    v
FastAPI <------ Next.js
```

## Límites de los módulos

- `packages/football_providers`: contrato con proveedores externos. El resto de la aplicación no
  conoce URLs ni cabeceras de API-Football.
- `apps/api/football_api/services/ingestion.py`: orquesta cargas incrementales, conserva RAW y aplica
  límites de consumo.
- `apps/api/football_api/services/predictions.py`: construye features point-in-time y versiona cada
  predicción.
- `packages/prediction_models`: matemáticas puras, sin dependencias de web o base de datos.
- `apps/api/football_api/routes.py`: contrato HTTP consumido por web y futuras apps móviles.
- `dbt`: transformaciones analíticas y comprobaciones de calidad fuera del camino transaccional.

## Decisiones de seguridad estadística

1. Solo se usan partidos con `kickoff_at` anterior al partido analizado.
2. La forma reciente se pondera exponencialmente y se regulariza contra el promedio de liga.
3. Un mercado de córners se omite cuando no hay al menos tres observaciones por lado.
4. Los amistosos reducen la confianza automáticamente.
5. Cada ejecución guarda features, versión del modelo y fecha de generación.
6. No se etiqueta una predicción como apuesta. Las oportunidades de valor exigen cuotas y un mínimo
   de confianza, y aun así necesitan backtesting temporal antes de usarse con dinero.

## Camino a producción

PostgreSQL puede migrarse a RDS, Neon o Supabase; Redis a un servicio gestionado; API y workers a
servicios de contenedores; Next.js a Vercel. Antes de compartir el sistema deben añadirse identidad,
roles, rate limiting, secretos gestionados, observabilidad, copias de seguridad y términos legales.

