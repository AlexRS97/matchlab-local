# Validación local del rework

Comprobaciones realizadas en Windows con Python 3.12 y Node.js 22. No sustituyen la
validación de cobertura y respuestas con credenciales reales de los proveedores.

## Código y navegación

- `scripts/check.ps1`: sintaxis PowerShell, Ruff y mypy correctos; **58 pruebas de backend** superadas (15 de septiembre de 2026).
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
Los nuevos casos comprueban que un fallo no alcanza el 100%, que actualizar datos respeta la configuración de entrenamiento automático y que las cinco familias emiten progreso antes de publicar sus artefactos.
Ese entrenamiento de prueba usa datos sintéticos y un directorio temporal; no reemplaza los modelos reales.

## Apertura, revisión automática y cierre (15 de septiembre de 2026)

- Comprobado el arranque manual con prioridad **Normal** en ambos procesos Python y en Node.
  La configuración del servicio y el reporte de entrenamiento registran **24 hilos**.
- Sin tareas programadas, entradas Run/RunOnce ni accesos directos del proyecto en las carpetas
  de inicio de Windows, tanto del usuario como comunes. No se instaló ningún mecanismo de autoarranque.
- Al abrir se incorporaron **48 partidos nuevos** y se activó el entrenamiento automáticamente.
  Se interrumpió durante la preparación de muestras mediante `stop.ps1`: quedaron **cero procesos
  Python/Node del proyecto y cero escuchas en 3000/8000**. DuckDB volvió a abrirse con 10.928 partidos
  y conservó el modelo previamente publicado (`920830904e794084bdc5743e856ccedd`).
- El siguiente arranque volvió a detectar los datos pendientes y completó las cinco familias.
  Una revisión posterior terminó al 100% sin reentrenar (`models_updated: false`), mantuvo la nueva
  versión y dejó `training_recommended: false`.
- Una prueba de integración verifica que el recálculo posterior respeta el bloqueo del refresco,
  guarda nuevas predicciones y rankings, y conserva el primer pronóstico de Performance.
  Otra comprueba que el aprendizaje no alcanza el 100% antes de aplicar los modelos.
- Cuatro pruebas de navegador superadas con entrenamiento real activo: navegación, jornada,
  móvil y progreso global con aviso de finalización. Durante la preparación de muestras se midieron
  6,67 segundos para `/api/today` y 1,81 segundos para el estado del progreso; por eso la prueba
  permite hasta 15 segundos para cargar los datos, sin esperar que desaparezcan los indicadores
  de trabajos activos. La barra mide fases, no tiempo restante.
- La notificación de la bandeja se añadió al script y pasó su comprobación de sintaxis. La limitación
  de la prueba de apertura de la bandeja descrita arriba sigue vigente; el aviso web sí se comprobó.

## Entrenamiento ejecutado

Versión local publicada: `ccb94b36110446458c714ad568297d17` (106.2 segundos).
Fuente: CSV públicos de Football-Data; cinco ligas, temporadas 2020/21 a 2026/27.
Histórico: **10.928 partidos**, con **10.453 muestras elegibles** hasta el 14 de septiembre de 2026.
PyTorch utiliza CPU; esta ejecución usó 24 hilos disponibles y prioridad normal.

| Bloque | Muestras | Periodo |
| --- | ---: | --- |
| Entrenamiento | 6.323 | 2020-10-02 a 2024-03-04 |
| Validación | 1.535 | 2024-03-08 a 2025-02-03 |
| Calibración | 1.004 | 2025-02-08 a 2025-10-17 |
| Test | 1.543 | 2025-10-20 a 2026-09-14 |

CatBoost, LightGBM, XGBoost, MLP y GRU se entrenaron, validaron y guardaron sin errores.
El ciclo terminó al 100% después de aplicar la versión publicada a la jornada disponible.
Sin credenciales de API-Football no hubo partidos actuales sobre los que medir ese recálculo real;
la prueba de integración cubre ese comportamiento con un partido aislado en memoria.

La selección general por validación eligió MLP para goles y GRU para córners; ambos blends del 20%
pasaron su control bootstrap por semanas. Los resultados son retrospectivos y no constituyen una
validación prospectiva independiente. Las decisiones específicas por liga y sus motivos se guardan
en el reporte y se muestran en Model Lab; no se declara un algoritmo ganador permanente.

## Revisión anterior con el perfil de ahorro

Las medidas de prioridad baja de esta sección corresponden a la revisión anterior. El usuario
cambió después su preferencia a capacidad completa mientras la aplicación está abierta; ese
perfil de ahorro ya no es la configuración activa.

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
- [CI en GitHub/Linux](https://github.com/AlexRS97/matchlab-local/actions/runs/34881196064)
  superado: instalación con versiones fijadas, Ruff, mypy, pytest, compilación y navegador.
  Se corrigió la instalación de PyTorch CPU para resolver sus dependencias desde PyPI.
- El controlador del acceso directo también comprueba cambios del código web antes de abrir;
  se verificó que reutiliza el bundle vigente y que el cierre termina sus procesos.

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
