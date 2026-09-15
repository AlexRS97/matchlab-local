# Metodología

## Datos anteriores al partido

Los modelos reciben resultados de partidos anteriores con `completed_at` y `observed_at` anteriores al inicio del encuentro objetivo. Se excluyen el propio encuentro, sus estadísticas, datos conocidos posteriormente y cuotas. Las predicciones de días pasados se leen de snapshots prepartido, no se reconstruyen con datos actuales.

Las ventanas son 5, 10 y 20 partidos y los splits casa/fuera se calculan aparte. La ausencia de xG, córners o tiros se conserva como ausencia. La media de liga necesita al menos 30 observaciones; la media de córners de liga exige su propia muestra suficiente. El H2H se muestra con su tamaño de muestra y no domina la estimación.

## Estadística

- **Poisson**: intensidades local/visitante mediante ataque y defensa relativos a las medias de liga, suavizados con un prior de cinco partidos. Combina perfil reciente y casa/fuera. Usa las colas analíticas para los Overs; la matriz visible 0–6 conserva una cola residual.
- **Dixon–Coles local**: corrección de las cuatro celdas de baja anotación, con rho estimado y regularizado sobre partidos previos de los equipos. Preserva masa total y marginales. Es una adaptación local; no se presenta como un ajuste global de fuerzas de todos los equipos de la liga. [Artículo original](https://doi.org/10.1111/1467-9876.00065).
- **Binomial negativa de goles**: marginales independientes con sobredispersión estimada y suavizada. Regresa a Poisson cuando no hay evidencia suficiente de dispersión adicional.
- **Forma reciente**: pesos por bloques de recencia, frecuencias regularizadas y perfiles de producción/concesión. Usa tendencias de tiros cuando existen suficientes datos.
- **Casa/fuera**: exclusivamente partidos del local en casa y del visitante fuera; exige al menos tres por lado.
- **xG**: usa xGF/xGA reales de ambos perfiles. Sin datos suficientes queda no disponible.
- **Córners**: Poisson, binomial negativa si la varianza supera suficientemente la media, forma reciente y casa/fuera. Exige datos reales de córners; no deriva córners de goles.

Los pesos están en `config/model_weights.yaml` y se renormalizan por mercado cuando falta un modelo. Son elecciones iniciales transparentes, no parámetros anunciados como óptimos. Algunos modelos comparten información y supuestos; su acuerdo no equivale a pruebas estadísticas independientes.

## Calidad y confianza

La calidad considera tamaño de muestra reciente y por sede, clasificación, tiros, xG, contexto de liga y frescura. Menos de cinco partidos válidos por equipo impide publicar la probabilidad del grupo correspondiente. Los datos insuficientes nunca entran en Top.

La confianza combina calidad, muestra y desacuerdo. Un desacuerdo alto o un split insuficiente limita la categoría. La puntuación de confianza no es una probabilidad de acertar ni un intervalo calibrado.

## Machine learning y deep learning

El histórico inicial incluye Premier League, Bundesliga, La Liga, Serie A y Ligue 1, desde 2020/21. La fuente son [CSV públicos de Football-Data](https://football-data.co.uk/data.php). Se importan únicamente resultados finales y estadísticas permitidas. Las cuotas presentes en los CSV originales no forman parte del dataset normalizado de aprendizaje.

Features: 76 variables de forma y sede, muestras, descanso y contexto de liga. No se introducen identificadores de equipo ni etiquetas del partido objetivo. Los resultados pasados se convierten en observaciones con un embargo conservador de 48 horas. **Es una reconstrucción retrospectiva**: la fuente no aporta un archivo auténtico de todas las fechas de publicación. No se afirma que esa disponibilidad temporal haya sido auditada partido a partido.

Se entrenan tres modelos de árboles (CatBoost, LightGBM y XGBoost) y dos redes PyTorch: MLP para datos tabulares y GRU para las últimas diez observaciones de cada equipo. Cada familia predice distribuciones de total de goles, BTTS y total de córners. La última clase de conteo agrupa la cola (6+ goles, 20+ córners), conservando las probabilidades de todas las líneas soportadas y su monotonía.

Las fechas se dividen en entrenamiento (60%), validación (15%), calibración (10%) y prueba final (15%), con dos días excluidos entre bloques. Los porcentajes se aplican a fechas únicas: los tamaños de muestra no tienen por qué coincidir exactamente. Imputación y escalado se ajustan solo en entrenamiento. El early stopping mira validación; no usa el test. La calibración por temperatura usa el tercer bloque. [Documentación de calibración](https://scikit-learn.org/stable/modules/calibration.html).

La familia ganadora de cada grupo se elige por Brier de validación antes de calibrar. Después se mide su mezcla 80% estadística / 20% aprendizaje en el bloque final. Para participar en producción, el intervalo bootstrap del 95% de la mejora debe quedar por encima de cero, con al menos 300 encuentros y 20 bloques semanales. El bootstrap remuestrea semanas completas, no partidos independientes.

Esta puerta de promoción utiliza el test, por lo que ese periodo deja de ser una verificación completamente independiente del proceso de despliegue. Reutilizar periodos en nuevos entrenamientos reduce aún más su independencia. **Performance** acumula la comprobación prospectiva que falta al backtest. Una mejora histórica pequeña no demuestra rentabilidad.

### Selección por liga

Para cada liga cubierta se comparan todos los modelos estadísticos con cobertura completa sobre
los mismos partidos y mercados de validación. El candidato debe superar al ensemble en ese bloque
y confirmar la mejora en calibración, con al menos 150 partidos y 20 semanas. El test no interviene
en la elección ni en la promoción estadística: evalúa después la política resultante.

La familia ML se elige de nuevo por liga con Brier de validación. La mezcla del 20% se compara
contra la referencia estadística aplicable en el test posterior, con 300 partidos y 20 semanas
como mínimos. Sus intervalos ajustan el nivel por las ligas y los dos grupos de mercados:
`1 - 0,05 / (2 × número de ligas)`. Con cinco ligas, el intervalo de cada control es del 99,5%.
Estos umbrales son decisiones del proyecto, no garantías universales de significación o rentabilidad.
Los controles bootstrap son aproximados y no corrigen la selección repetida a lo largo de futuros
entrenamientos. Un candidato rechazado no sustituye al modelo estadístico. Sin comparación local
suficiente se conserva la referencia general. Model Lab muestra ambas comparaciones explícitamente.

Los resultados y el dataset guardan el código de liga y todos los candidatos estadísticos,
incluidos valores ausentes. La inferencia aplica esa selección a la liga del encuentro. Si la
referencia estadística promovida no está disponible para un partido, también se desactiva su blend
ML, ya que su evaluación correspondía a otra referencia.

Se registran Brier, log loss, ECE y un diagnóstico logístico de calibración con statsmodels (intercepto y pendiente). Este último describe el resultado de la evaluación; no se aplica a las predicciones. El Brier de grupo promedia líneas; BTTS No se excluye de ese promedio para no contar dos veces el mismo evento. [GLM de statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.genmod.generalized_linear_model.GLM.html).

Los artefactos se guardan en formatos nativos y pesos PyTorch con carga `weights_only=True`, junto con dataset, preprocesador, cortes temporales, pesos estadísticos y reporte. Se verifica la recarga antes de publicar la versión. La inferencia comprueba liga, muestra, antigüedad del modelo y proporción de datos faltantes; se abstiene si no cumple. La versión debe haberse creado antes del partido. Se utiliza el ajuste evaluado, sin un refit posterior que invalidaría las métricas publicadas: las fechas exactas de ajuste y calibración son visibles en Model Lab.

## Actualización diaria frente a entrenamiento

Cada día se actualizan partidos, sus datos previos y sus predicciones; no hace falta reentrenar para aplicar un modelo a la nueva jornada. Se conserva el primer pronóstico para medir rendimiento, y se guardan los recálculos en snapshots separados.

El histórico y la vigencia de los modelos se comprueban al abrir y a diario mientras la aplicación esté abierta. El arranque y el cierre son manuales; con MatchLab detenido no hay actualizaciones. `automatic_training: true` en `config/learning.yaml` activa el entrenamiento si falta una versión, cambia la revisión del histórico (incluidas correcciones) o el modelo alcanza 45 días. Para reportes antiguos sin revisión se aplica el umbral de un día y un partido nuevo. Sin cambios se reutilizan los modelos vigentes; el botón de Model Lab permite forzar un entrenamiento. Se aprovechan automáticamente los procesadores disponibles. El cierre manual termina el entrenamiento en curso. Un fallo antes de publicar conserva la versión anterior; si falla el recálculo posterior, se muestra el error y la nueva versión publicada permanece disponible. El 100% incluye la aplicación de los modelos a la jornada.
