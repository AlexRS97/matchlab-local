# Experimento: <hipótesis breve>

Estado: propuesto / en curso / terminado / descartado. Autor, fecha e issue o PR:

## Hipótesis y criterio previo

Problema concreto, ligas y mercados. ¿Qué cambiará y por qué podría mejorar? Define antes de
medir el criterio de aceptación, el coste máximo y qué resultado hará descartar el candidato.
Este documento es una plantilla: no contiene resultados ejecutados.

## Fuentes e investigación

Artículos originales y documentación oficial, con enlace, fecha de consulta y hallazgo aplicable.
Distingue resultados publicados, interpretación propia y lo que realmente implementaste.
Para una fuente nueva: cobertura por liga/temporada, campos ausentes, fechas de publicación,
correcciones, correspondencia de equipos, límites de acceso y condiciones de uso.

## Reproducción

| Campo | Valor |
| --- | --- |
| Commit y estado de los cambios locales | |
| Entorno: sistema, Python, paquetes, CPU/GPU e hilos | |
| Configuración, semilla y comando o script de ejecución | |
| Identificador y huella del dataset; fuente y fecha de extracción | |
| Snapshot congelado o histórico actualizado durante la ejecución | |
| Periodos de entrenamiento, validación, calibración y evaluación | |
| Embargo y disponibilidad real o supuesta de las observaciones | |
| Muestras y ausencias por liga y mercado | |
| Referencia estadística y modelo publicado usados para comparar | |
| Identificadores de los runs y ubicación privada de los reportes | |
| Tiempo de entrenamiento e inferencia y consumo de memoria medido | |

Las versiones y huellas se pueden recuperar de `report.json`; documenta cualquier diferencia
que el reporte no capture. No subas CSV, modelos, credenciales ni snapshots privados al repositorio.

## Resultados comparables

| Liga / mercado / periodo | Partidos comunes | Brier referencia / candidato | Log loss referencia / candidato | Calibración y cobertura | Intervalo y método |
| --- | ---: | --- | --- | --- | --- |
| | | | | | |

Incluye ablaciones cuando ayuden a atribuir la diferencia a un cambio, decisiones de early
stopping, búsquedas realizadas y ajustes por comparaciones múltiples. Indica si el test se ha
consultado en experimentos previos. Las tablas vacías no son evidencia de mejora.

## Decisión y límites

Aceptar para evaluación posterior / mantener la referencia / descartar. Razones, fallos,
sensibilidad por liga, coste y datos que faltan. Indica qué periodo prospectivo queda sin
consultar y qué comprobación falta antes de proponer el cambio para uso diario.

## Verificación

Comandos de comprobación ejecutados, resultados y pruebas relevantes. Efectos en contratos,
actualización diaria, progreso, recursos y cierre. Enlaza el PR y la documentación modificada.
