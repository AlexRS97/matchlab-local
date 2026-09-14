# Mercados y cálculos

Todos los mercados de la versión activa son de tiempo reglamentario, prepartido.

| Grupo | Mercados |
|---|---|
| Total de goles | Over 0.5, 1.5, 2.5, 3.5, 4.5 |
| Ambos marcan | Sí y No |
| Total de córners | Over 7.5, 8.5, 9.5, 10.5, 11.5 |

La selección contraria Under/No puede almacenarse para retirar proporcionalmente el margen del bookmaker. Se utilizan dos precios de la misma casa/proveedor, ambos recientes y separados por un máximo de 60 segundos. Si falta el otro lado, se muestra la implícita bruta con `NOT_DEVIGGED`.

- Probabilidad implícita: `1 / cuota`.
- Probabilidad Over sin margen: `(1 / over) / ((1 / over) + (1 / under))`.
- Cuota justa: `1 / probabilidad_modelo`.
- Edge: `probabilidad_modelo - probabilidad_mercado`, en puntos porcentuales.
- EV bruto: `probabilidad_modelo * cuota - 1`.

Ejemplo: p=0,72 y cuota=1,55 producen cuota justa≈1,389 y EV=11,6%. Son cálculos condicionados a la probabilidad estimada, sin garantía de beneficio.

El ranking ordena primero por probabilidad; utiliza confianza, calidad y EV para desempatar. No ordena prioritariamente por EV. La cuota mínima inicial es 1,35; no se muestran en Top encuentros iniciados ni con datos insuficientes, incluso si se relajan otros filtros. Todos permanecen consultables en la tabla general.

La mejor cuota se elige entre las casas habilitadas con precio fresco. Si todas son antiguas, pueden verse como STALE en el detalle pero no sostienen un Top Pick. El consenso de mercado se calcula por separado y no entra en el ensemble deportivo.

Las líneas asiáticas con devolución, mercados de equipo, primera parte y prórroga no se convierten silenciosamente en los mercados anteriores. Se descartan hasta disponer de un contrato y cálculo específicos.
