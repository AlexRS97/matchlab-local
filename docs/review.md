# Revisión del proyecto · 14 septiembre 2026

## Arquitectura y limpieza

La aplicación utiliza FastAPI, DuckDB, React y Vite. Se han retirado la API antigua, Next.js,
PostgreSQL, Redis/Celery, dbt, migraciones, contenedores, pruebas y documentación de ese stack.
Se mantienen la licencia, los avisos de terceros, las políticas del repositorio y el logo reutilizado
en `assets/`. Las credenciales, históricos y modelos pertenecen al almacenamiento local y no a GitHub.
El historial Git conserva las revisiones anteriores.

La revisión automática bloqueó el borrado de la copia antigua del PNG. Esa copia permanece en
disco bajo `apps/`, ignorada por Git; el instalador utiliza exclusivamente `assets/`. Los restos
generados de dbt también se excluyen de la publicación.

## Cambios aplicados

| Hallazgo | Cambio |
| --- | --- |
| Mismos criterios generales para todas las ligas | Selección estadística y ML por liga y grupo de mercados, con muestras mínimas, periodos separados y controles de mejora |
| Reimportar todos los CSV reescribía filas sin cambios | Huella del contenido normalizado y reemplazo atómico de cada liga/temporada; una repetición sin cambios no escribe partidos |
| Un CSV truncado o duplicado podía degradar el histórico | Rechazo de duplicados y reducción de filas, rollback y conservación del último CSV válido |
| Una corrección de fecha dejaba un partido antiguo | Sustitución de la partición completa validada, sin duplicar el encuentro corregido |
| Poca visibilidad de la cobertura | Último resultado y número de partidos por liga, nuevos partidos desde el entrenamiento, edad del modelo y recomendación de entrenamiento manual |
| Artefactos difíciles de reproducir | Huellas de datos y código, versiones de bibliotecas, configuración, semilla y periodos guardados por ejecución |
| Repetición de inferencias y compilación al abrir | Caché acotada por versión, liga y variables; reutilización de la web compilada mientras no cambien sus fuentes |
| Competencia por CPU | Dos hilos de cálculo y DuckDB, prioridad baja en Windows, redes en CPU y entrenamiento manual |
| Performance mezclaba probabilidades pendientes y resueltas | Media, Brier y log loss sobre los mismos partidos resueltos; intervalo Wilson del 95% y aceptación de resultados corregidos |
| Automatizaciones del stack retirado | CI de backend/web/navegador, auditorías nativas, versiones Python verificadas y dependencias web fijadas |

El intervalo Wilson describe la frecuencia observada bajo una aproximación binomial. No es un
intervalo de rentabilidad y no modela la dependencia temporal entre partidos. Las promociones de
modelos usan remuestreo de semanas completas por separado.

## Cómo se elige por liga

Las comparaciones actuales cubren Premier League, Bundesliga, La Liga, Serie A y Ligue 1.
La cartelera puede incluir más ligas según API-Football; fuera del histórico entrenado se conserva
la referencia estadística y se exige muestra suficiente para calcularla.

1. Reconstruir variables anteriores a cada partido con embargo de 48 horas.
2. Elegir el candidato estadístico por Brier de validación sobre los mismos partidos y mercados.
3. Activarlo solo si mejora al ensemble en calibración: mínimo 150 partidos y 20 semanas.
4. Elegir la familia ML de cada liga por validación y calibrar sus probabilidades en otro periodo.
5. Evaluar el blend del 20% contra la referencia estadística aplicable en el test posterior:
   mínimo 300 partidos, 20 semanas e intervalo de mejora positivo.

Los controles por liga ajustan el nivel del intervalo por el número de ligas y grupos comparados
(99,5% con cinco ligas y dos grupos). La selección se renueva cuando se entrena. La falta de mejora
confirmada conserva la referencia; un nombre de algoritmo no equivale a superioridad demostrada.
El test utilizado para autorizar un blend deja de ser completamente independiente del despliegue,
y reutilizarlo al reentrenar reduce su valor como evidencia. Véase [metodología](methodology.md).

Separar el tiempo evita entrenar con observaciones posteriores a las que se evalúan; también hay
que ajustar el tratamiento de las probabilidades fuera de los datos de ajuste del modelo.
Referencias: [validación temporal de scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
y [calibración](https://scikit-learn.org/stable/modules/calibration.html).

## Fuentes y actualización

Se mantiene API-Football para datos operativos, Football-Data para resultados históricos,
Betfair oficial para Exchange y PulseScore para Bet365/Winamax. La selección debe atender a
cobertura, fecha de publicación, completitud y licencia, no solo al número de campos.
[Football-Data describe el contenido de sus CSV](https://www.football-data.co.uk/data).

Al abrir se actualiza lo que haya vencido. Mientras esté abierto, se revisan partidos cada
30 minutos, Betfair cada cinco y PulseScore según su presupuesto efectivo. El histórico actual
se comprueba cada día; temporadas cerradas usan caché prolongada. Una consulta reciente no implica
que el proveedor haya publicado un resultado nuevo. Las marcas temporales y los fallos son visibles.

Las credenciales operativas siguen pendientes: no se ha podido verificar cartelera y cuotas
reales autenticadas. No se han contratado servicios ni añadido fuentes cuya cobertura no esté
verificada. [Configuración y límites](providers.md).

## Siguientes mejoras con mayor valor

Estas propuestas son trabajo futuro, no prestaciones anunciadas como terminadas:

- **Evaluación temporal repetida** con ventanas móviles y un periodo prospectivo nuevo para cada
  promoción; comparar también con el modelo ya publicado, no solo con la referencia estadística.
- **Detección de cambio de distribución** por liga: evolución de Brier/calibración y datos faltantes,
  con tamaño mínimo antes de mostrar alertas.
- **Datos de eventos y xG con cobertura comprobada**. El repositorio oficial de
  [StatsBomb Open Data](https://github.com/hudl/open-data) ofrece competiciones seleccionadas,
  eventos y alineaciones; no constituye una fuente diaria universal. Un adaptador requiere
  comprobar licencia, temporadas e identidad de equipos antes de combinar históricos.
- **Modelos jerárquicos dinámicos** para compartir información entre equipos y temporadas,
  comparados con los actuales bajo el mismo protocolo. Su coste adicional debe justificarse
  mediante mejoras temporales medibles; la [investigación sobre modelos dinámicos](https://academic.oup.com/jrsssd/article/51/2/157/7120674)
  aporta una línea de trabajo, no una garantía para estas ligas y mercados.
- **Cuotas de cierre y comisión efectiva** para CLV y evaluación económica prospectiva, una vez
  exista captura real consistente. No reconstruir cuotas que nunca se guardaron.

Evidencia de esta entrega: [validación local](validation.md).
