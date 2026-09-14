# Estado del rework Football Analytics AI

La aplicación activa utiliza `backend/` (FastAPI + DuckDB), `frontend/` (React + Vite)
y `config/`. Se retiró el código anterior; las credenciales y los datos locales se conservan fuera de Git.
El alcance parte de las 92 indicaciones y añade el aprendizaje y el análisis diario solicitados.

## Implementación y validación local

- [x] Fase 1: configuración, contratos, DuckDB, FastAPI, Vite y pruebas de arranque.
- [x] Fase 2: adaptador API-Football, cartelera por fecha Madrid, histórico, splits y clasificación.
- [x] Fase 3: modelos independientes de goles, ensemble, calidad, confianza y tabla ordenable.
- [x] Fase 4: Betfair de solo lectura, PulseScore, matching, snapshots, comparación y cuotas manuales.
- [x] Fase 5: Top 5, grupos de mercados, filtros y cálculo de valor separado del modelo.
- [x] Fase 6: detalle, distribuciones, forma, H2H, clasificación y explicación determinista en español.
- [x] Fase 7: estadísticas y modelos de córners, ensemble y rankings.
- [x] Fase 8: scheduler, caché, presupuestos, circuit breaker, ajustes, resultados y arranque Windows.
- [x] Validación local: 52 pruebas de backend, Ruff, mypy, build y cuatro pruebas de navegador.

Estas casillas describen código implementado y pruebas locales. Los contratos de los proveedores
se prueban con respuestas controladas; la aceptación con cuentas reales sigue pendiente abajo.

## Machine learning, deep learning y ciclo diario

- [x] Importación de CSV históricos públicos de Football-Data, sin columnas de cuotas en los modelos.
- [x] CatBoost, LightGBM y XGBoost entrenados y persistidos en sus formatos nativos.
- [x] PyTorch: MLP y GRU con parada temprana y persistencia de pesos.
- [x] Corrección local regularizada Dixon–Coles y marginales independientes de goles binomial negativa.
- [x] División cronológica con embargo; calibración separada y evaluación Brier, log loss y calibración.
- [x] Selección en validación y evaluación del blend frente al modelo estadístico mediante bootstrap semanal.
- [x] Model Lab y detalle con versión, cobertura, comparación de candidatos y probabilidades identificadas.
- [x] Primer entrenamiento real: 10.880 partidos históricos y 10.413 muestras elegibles.
- [x] Actualización diaria del histórico con la app abierta; reentrenamiento manual por preferencia del usuario.
- [x] Actualización y recálculo diario de la jornada a las 06:00 Europe/Madrid, con recuperación al arrancar.
- [x] Estado diario persistente, errores visibles y actualización adicional durante el día.
- [x] Panel global de progreso con porcentajes, fases y contadores de archivos, objetivos y épocas.
- [x] Worker temporal para actualizar con la aplicación cerrada y reutilización de la API cuando está abierta.
- [x] Arranque manual, dos hilos, prioridad baja y reutilización del bundle para reducir carga al abrir.
- [x] Comparación estadística y ML por liga, importaciones incrementales verificadas y trazabilidad de entrenamientos.

## Pendiente de configuración externa

- [ ] Configurar API_FOOTBALL_KEY y verificar fixtures, cobertura estadística y límites de la cuenta real.
- [ ] Configurar Betfair y PulseScore; verificar precios y matching con los mercados de las cuentas reales.
- [ ] Acumular evaluación prospectiva con predicciones publicadas antes del partido y resultados reales.

Sin las claves, el ciclo registra la falta de datos; no afirma haber cargado la jornada. El histórico
de aprendizaje no sustituye la cartelera diaria ni proporciona cuotas actuales.

## Decisiones y límites

- Inicio y cierre manuales para liberar recursos al jugar. No se instala la tarea de Windows.
  El reentrenamiento automático queda desactivado; los modelos guardados siguen disponibles.

- PulseScore identifica Orbit Exchange por separado: el fallback no se presenta como Betfair oficial.
- El refresco respeta los presupuestos: una cuenta limitada puede dejar cobertura parcial o cuotas antiguas.
- Los resultados deportivos y la disponibilidad temporal condicionan cada predicción. Las cuotas no
  entran en los modelos; no hay apuestas automáticas ni scraping de las casas.
- El histórico CSV es retrospectivo: el embargo de 48 horas aproxima la publicación de estadísticas.
  Su evaluación no equivale a resultados prospectivos y pierde independencia si se reutiliza el test.
- Los modelos aprendidos solo participan si pasan los controles; su peso máximo es del 20%.
  Ningún algoritmo se presenta como el mejor universal.
- Performance y calibración ya están implementados. Ollama, más casas, CLV y las otras extensiones
  de la hoja de ruta permanecen opcionales.

Evidencia reproducible: [validación](validation.md). Funcionamiento: [README](../README.md).
