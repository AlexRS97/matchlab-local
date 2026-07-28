# Guía técnica de desarrollo

## Criterio para comentarios

Un comentario profesional explica aquello que el código no puede expresar por sí mismo:

- invariantes de negocio;
- decisiones de seguridad;
- regularización o supuestos estadísticos;
- comportamiento temporal y zonas horarias;
- límites de proveedores y efectos laterales;
- razones por las que una alternativa aparentemente sencilla no es válida.

No se repite con texto una asignación, condición o nombre claro. Los comentarios obsoletos son un
riesgo: todo cambio debe actualizar código, pruebas y documentación en el mismo pull request.

## Capas

- `packages/prediction_models`: funciones matemáticas puras y deterministas.
- `packages/football_providers`: adaptadores HTTP; no contienen reglas del producto.
- `services/ingestion.py`: orquestación, cuotas de proveedor y persistencia incremental.
- `services/predictions.py`: features point-in-time y persistencia de versiones.
- `services/recommendations.py`: presentación conservadora de señales y valor.
- `routes.py` y `schemas.py`: contrato HTTP, sin matemáticas duplicadas.
- `apps/web`: composición visual y consumo tipado del contrato.
- `dbt`: modelos analíticos fuera del camino transaccional.

## Reglas de diseño

- Las predicciones solo utilizan información conocida antes de `kickoff_at`.
- Toda operación externa debe definir timeout y traducir errores del proveedor.
- Las escrituras repetibles deben ser idempotentes o usar claves naturales.
- El dinero, si se incorpora, utiliza tipos decimales y nunca `float`.
- Las fechas persistidas son UTC; la presentación aplica `Europe/Madrid`.
- No se registra el cuerpo de solicitudes que pueda contener credenciales.
- Una recomendación no se representa como certeza ni se genera sin umbral de calidad.

## Definición de terminado

Un cambio está terminado cuando:

1. tiene pruebas proporcionales al riesgo;
2. Ruff, mypy, pytest y la compilación web pasan;
3. no añade vulnerabilidades altas conocidas ni secretos;
4. actualiza contratos y documentación;
5. incluye migración reversible si cambia el esquema;
6. mantiene el modo demostración;
7. ha sido revisado en escritorio y móvil si modifica la interfaz.

## Versionado

Se recomienda SemVer:

- `MAJOR`: cambio incompatible de API o modelo persistido;
- `MINOR`: función compatible;
- `PATCH`: corrección compatible.

Las versiones de producción deben usar tags firmados y notas de cambios. Las imágenes deben
publicarse por digest y conservar un SBOM.
