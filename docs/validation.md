# Validación local del rework

Comprobaciones realizadas en Windows con Python 3.12 y Node.js 22. No sustituyen la
validación de cobertura y respuestas con credenciales reales de los proveedores.

## Código y navegación

- `scripts/check.ps1`: sintaxis PowerShell, Ruff y mypy correctos; **52 pruebas de backend** superadas.
- TypeScript y compilación Vite correctos.
- **4 pruebas Playwright**: navegación principal, jornada con seis partidos y Top 5 con búsqueda/detalle,
  diseño móvil a 390 px y progreso de actualización/entrenamiento hasta el 100% con avisos.
- Escenario de navegador generado en memoria e interceptado: no se escriben fixtures ficticios en
  `data/football.duckdb`.
- Arranque mediante `scripts/matchlab-control.ps1 -Action Start -NoBrowser` comprobado.
- Arranque y cierre manuales con `start.ps1` y `stop.ps1` comprobados. La prueba de apertura de la
  bandeja fue rechazada por la revisión automática; los accesos directos están creados.
- Worker diario con aplicación cerrada comprobado: actualiza, persiste estado y termina sin servidores.
- Interrupción manual de un worker en curso con `stop.ps1` comprobada: cero procesos Python/Node
  del proyecto y cero escuchas en 3000/8000. DuckDB vuelve a abrirse y conserva los 10.880 partidos;
  el identificador de los modelos publicados permanece intacto.
- Ciclo diario a través de la API abierta comprobado: termina sin abrir otro proceso sobre DuckDB y
  conserva por separado el estado de partidos/análisis y la actualización del histórico.

Las pruebas incluyen probabilidades y colas de distribución, calibración, renormalización, cuotas
y de-vig, matching, datos ausentes, fallos/cuotas de proveedores, caché, cambio de día y horario de
verano, recálculo diario forzado y conservación de snapshots cuando desaparece una selección.
Los nuevos casos comprueban que un fallo no alcanza el 100%, que actualizar datos no entrena
automáticamente y que las cinco familias emiten progreso antes de publicar sus artefactos.
Ese entrenamiento de prueba usa datos sintéticos y un directorio temporal; no reemplaza los modelos reales.

## Entrenamiento ejecutado

Versión local final: `920830904e794084bdc5743e856ccedd` (130,3 segundos).
Fuente: CSV públicos de Football-Data; cinco ligas, temporadas 2020/21 a 2026/27.
Se importaron **10.880 partidos**, con **10.413 muestras elegibles**.

| Bloque | Muestras | Periodo |
| --- | ---: | --- |
| Entrenamiento | 6.275 | 2020-10-02 a 2024-02-28 |
| Validación | 1.513 | 2024-03-03 a 2025-01-31 |
| Calibración | 1.010 | 2025-02-03 a 2025-10-05 |
| Test | 1.548 | 2025-10-17 a 2026-09-07 |

CatBoost, LightGBM, XGBoost, MLP y GRU se entrenaron y guardaron. La recarga de sus artefactos
y la repetición de inferencia sobre el test reprodujeron las métricas guardadas.
La selección general por validación eligió MLP para goles y CatBoost para córners. Ambos blends
del 20% superaron la referencia general en el control bootstrap por semanas de esta ejecución.
Los diez controles específicos por liga/grupo no confirmaron mejora con sus criterios más estrictos;
en esas ligas se conserva la referencia estadística. Model Lab muestra candidatos y motivos.

| Grupo | Brier de referencia | Brier del blend |
| --- | ---: | ---: |
| Goles | 0,176956 | 0,176382 |
| Córners | 0,224998 | 0,224132 |

Son mejoras pequeñas en un histórico retrospectivo, con publicación aproximada mediante embargo
de 48 horas. El test utilizado para promoción no representa una evaluación prospectiva independiente.
Los reportes completos incluyen log loss, calibración, métricas por mercado y limitaciones.

## Revisión final y consumo local

- 52 pruebas de backend y cuatro de navegador superadas tras añadir importaciones atómicas,
  corrección de resultados, cohorte de Performance, caché y selección temporal por liga.
- Ruff y mypy correctos (92 módulos de aplicación); TypeScript/Vite correctos.
- La repetición de los 35 CSV revisó 10.880 partidos en 0,585 segundos: cero descargas,
  cero particiones modificadas y ninguna pérdida de filas.
- Arranque medido: 6,86 segundos, reutilizando la compilación existente. En reposo, tras actualizar
  sin claves operativas, Python y Node sumaron aproximadamente 268 MB; prioridad BelowNormal
  verificada tanto en el proceso Python efectivo como en la web. El entrenamiento y la inferencia
  con modelos cargados consumen más memoria; estas cifras no miden una jornada completa autenticada.
- Cierre verificado: cero procesos Python/Node del proyecto y cero escuchas en 3000/8000.
  Una actualización CLI posterior terminó con código 0, manteniendo la versión de modelos publicada.
- Accesos directos regenerados desde el logo conservado en `assets/`.
- Gitleaks no encontró secretos en 19 commits previos ni en los cambios preparados. Auditorías
  Python y npm sin vulnerabilidades conocidas en el momento de la comprobación.
- Existen avisos de deprecación en bibliotecas de pruebas y LightGBM; no fallaron los checks.

La revisión automática bloqueó eliminar la copia antigua del logo. Se excluyó del índice y de
la publicación; no se usa desde la aplicación. Véase [revisión](review.md).

## Límites de la comprobación operativa

API-Football, Betfair y PulseScore no tienen credenciales configuradas en este entorno. Por tanto,
la ejecución diaria registra la ausencia de API_FOOTBALL_KEY y no afirma haber descargado partidos
actuales. El histórico público sí se descargó y entrenó realmente.

La revisión automática rechazó registrar la tarea de Windows con «blocked by policy».
Posteriormente el usuario eligió arranque y cierre manuales, por lo que instalar esa tarea ya no
forma parte del alcance. Se comprobó que no hay tareas ni entradas de inicio automático para
este proyecto. El scheduler del backend y el worker manual siguen disponibles bajo control del usuario.
